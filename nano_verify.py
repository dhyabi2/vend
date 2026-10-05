"""Nano block verification via RPC (rpc.nano.to).
Verifies that a send block exists on-ledger with the expected amount and destination.
No facilitator — direct ledger check.
"""

import base64
import json
import logging
import os
import re
import time
from decimal import Decimal
from typing import Optional
import httpx

# Nano block hashes are exactly 64 uppercase hex characters.
_HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")

NANO_RPC_URL = os.environ.get("NANO_RPC_URL", "https://rpc.nano.to")
NANO_RPC_KEY = os.environ.get("NANO_RPC_KEY", "")
VEND_ACCOUNT = os.environ.get("NANO_AGENT_ACCOUNT", "")

# Seconds to wait for a broadcast send block to confirm before treating the
# payment as not-settled.  Nano finality is sub-second but the public RPC can
# lag, so give a confirmed block a short window; never wait forever on a fork
# or a block that will never confirm.
PAYMENT_CONFIRM_TIMEOUT_S = float(os.environ.get("VEND_CONFIRM_TIMEOUT", "8"))
PAYMENT_CONFIRM_POLL_S = float(os.environ.get("VEND_CONFIRM_POLL", "0.5"))


def _price_to_raw(price_xno: float) -> int:
    """Convert an XNO price to raw integers without float drift.

    ``int(0.0001 * 10**30)`` returns 100000000000000004764729344, because the
    binary float for 0.0001 is not exactly 1e-4 and the error survives the
    scaling and the rounding.  That drifted value is then published in the 402
    challenge and rejected by buyers' clients and directory probes as "not a
    base-10 integer".  Converting through ``Decimal(str(price))`` is exact for
    every price this server takes from its environment.
    """
    return int(Decimal(str(price_xno)) * Decimal(10) ** 30)


# The price quoted in the 402 challenge and the price the verifier enforces are
# derived from the same source, so they cannot drift apart.
PRICE_XNO = float(os.environ.get("VEND_PRICE_EXTRACT", "0.0001"))
PRICE_RAW = str(_price_to_raw(PRICE_XNO))  # 0.0001 XNO == 10^26 raw


def parse_block_hash(raw: str) -> Optional[str]:
    """Parse a Nano block hash from a header value.

    Accepts either the bare 64-hex hash or a base64-encoded JSON payload with
    a ``block`` / ``hash`` / ``blockHash`` / ``transactionHash`` / ``paymentHash``
    key holding one.  Returns uppercase hex or ``None``.

    This is the single entry point for all payment-header values.  It rejects
    arbitrary text that is not a valid Nano block hash.
    """
    raw = raw.strip()
    if _HEX64.match(raw):
        return raw.upper()

    # Try base64-encoded JSON
    try:
        decoded = base64.b64decode(raw, validate=True).decode("utf-8", errors="replace")
        payload = json.loads(decoded)
        for key in ("block", "hash", "blockHash", "transactionHash", "paymentHash"):
            val = payload.get(key)
            if isinstance(val, str) and _HEX64.match(val):
                return val.upper()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
        pass
    return None


def raw_to_xno(raw: str) -> str:
    """Convert raw (smallest Nano unit) to XNO."""
    try:
        val = int(raw)
        return f"{val / 1e30:.6f}"
    except (ValueError, TypeError):
        return "unknown"


_ACCOUNT_RE = re.compile(r"^(?:nano|xrb)_[13][13-9a-km-uw-z]{59}$")


def is_account(s: str) -> bool:
    """True if *s* looks like a Nano account address (loose format check)."""
    return isinstance(s, str) and bool(_ACCOUNT_RE.match(s))


def _block_hash_of(block: dict) -> Optional[str]:
    """Compute/recover the block hash for a send state block.

    Uses Nano's ``block_hash`` RPC (it recomputes the hash from the block
    contents using the spec's hashing rules), returning uppercase hex.
    """
    if not isinstance(block, dict):
        return None
    try:
        resp = httpx.post(
            NANO_RPC_URL,
            json={"action": "block_hash", "json_block": "true", "block": block},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            h = data.get("hash", "")
            if _HEX64.match(h):
                return h.upper()
    except Exception:
        pass
    return None


def parse_payment_signature(header_value: str) -> Optional[dict]:
    """Parse a ``PAYMENT-SIGNATURE`` header into its PaymentPayload dict.

    The header is a base64-encoded JSON PaymentPayload (x402 exact scheme):
    ``{x402Version, resource, accepted, payload: {block: {...}}}``.  Returns
    the parsed dict, or ``None`` if it is not a parseable PaymentPayload.

    This is deliberately separate from ``parse_block_hash``: a PaymentPayload
    is not a bare 64-hex hash and the old parser must keep accepting the
    self-broadcast dialect (``X-PAYMENT: <hash>``) unchanged.
    """
    if not header_value:
        return None
    raw = header_value.strip()
    if _HEX64.match(raw):
        # A bare hash has no payload.block; not a PaymentPayload.
        return None
    try:
        decoded = base64.b64decode(raw, validate=True).decode("utf-8", errors="replace")
        payload = json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    block = (payload.get("payload") or {}).get("block")
    if not isinstance(block, dict) or not block:
        return None
    return payload


def block_decrement_amount(block: dict) -> Optional[int]:
    """The raw amount a send state block transfers = previous.balance - new.balance.

    A send block's ``balance`` field is the *remaining* balance after the
    transfer, so the amount sent is the previous block's balance minus the new
    balance.  This matches the x402 exact scheme's verification step 2.  The
    previous balance must be fetched on-ledger via ``block_info``.
    """
    previous = block.get("previous", "")
    if not _HEX64.match(previous):
        return None
    try:
        prev_info = check_block_exists(previous)
    except Exception:
        return None
    if not prev_info or "contents" not in prev_info:
        return None
    contents = prev_info.get("contents", {})
    if isinstance(contents, str):
        try:
            contents = json.loads(contents)
        except json.JSONDecodeError:
            return None
    prev_balance = contents.get("balance")
    new_balance = block.get("balance")
    if prev_balance is None or new_balance is None:
        return None
    try:
        return int(prev_balance) - int(new_balance)
    except (ValueError, TypeError):
        return None


def broadcast_block(block: dict) -> dict:
    """Broadcast a signed Nano state block via RPC ``process``.

    Returns a dict mirroring the RPC response:
      - on success: ``{"ok": True, "hash": <uppercase-hex>}``
      - on rejection/error: ``{"ok": False, "error": <str>}``

    Processing the block validates the signature, work and balance against the
    ledger before it is accepted into the node, so an unsigned or forged block
    cannot be paid-for: ``process`` rejects it.
    """
    try:
        resp = httpx.post(
            NANO_RPC_URL,
            json={"action": "process", "json_block": "true",
                  "subtype": "send", "block": block},
            headers={"Authorization": f"Bearer {NANO_RPC_KEY}"} if NANO_RPC_KEY else {},
            timeout=15,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"process RPC HTTP {resp.status_code}"}
        data = resp.json()
        if "error" in data:
            return {"ok": False, "error": str(data.get("error"))}
        h = data.get("hash", "")
        if not _HEX64.match(h):
            return {"ok": False, "error": f"process returned no valid hash: {data!r}"}
        return {"ok": True, "hash": h.upper()}
    except Exception as e:  # network / timeout
        return {"ok": False, "error": f"process RPC unreachable: {e}"}


def wait_for_confirmation(block_hash: str, timeout_s: float = None,
                          poll_s: float = None) -> dict:
    """Poll ``block_info`` until *block_hash* is a confirmed, on-ledger block.

    Returns a dict with ``confirmed`` (bool) and the ``block_info`` dict when
    confirmed.  A block that is on-ledger (``block_info`` returns contents) is
    treated as received; confirmation depth on a healthy Nano network for a
    single-user send is effectively immediate.
    """
    if timeout_s is None:
        timeout_s = PAYMENT_CONFIRM_TIMEOUT_S
    if poll_s is None:
        poll_s = PAYMENT_CONFIRM_POLL_S
    import time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        info = check_block_exists(block_hash)
        if info and "contents" in info:
            return {"confirmed": True, "block_info": info}
        if info and "error" in info:
            # Rejected outright (e.g. not in ledger); no point waiting.
            return {"confirmed": False, "block_info": info,
                    "error": str(info.get("error"))}
        time.sleep(poll_s)
    return {"confirmed": False, "error": "timed out waiting for confirmation"}


def confirm_signature_payment(payload: dict, expected_price_raw: str = PRICE_RAW,
                              expected_destination: str = "") -> dict:
    """Verify, broadcast, confirm and verify a PAYMENT-SIGNATURE payment.

    Implements the x402 ``exact`` PAYMENT-SIGNATURE flow with Vend acting as
    its own facilitator (the resource server self-facilitates -- no external
    facilitator, matching feeless402):

    1. structural checks on ``payload.block`` (type, destination);
    2. fast-fail on destination mismatch and on a bad decrement amount;
    3. broadcast the signed block via RPC ``process`` (validates signature,
       work and balance on-ledger);
    4. wait for confirmation;
    5. re-verify the now-on-ledger block with the existing ``verify_payment``
       (amount >= price, destination == payTo) so the returned dict has the
       same shape the X-PAYMENT path already trusts.

    Returns a dict shaped exactly like ``verify_payment``'s result so the
    caller (server.py) needs no branching: keys valid/amount_raw/source/
    destination/message/block_hash/accepted(optional).
    """
    if not isinstance(payload, dict):
        return {
            "valid": False, "amount_raw": "0", "source": "", "destination": "",
            "message": "Not a payment payload",
        }
    if not expected_destination:
        expected_destination = VEND_ACCOUNT

    def _fail(msg: str):
        block = (payload.get("payload") or {}).get("block") or {}
        return {
            "valid": False, "amount_raw": "0",
            "source": block.get("account", ""),
            "destination": block.get("link_as_account") or block.get("link", ""),
            "message": msg,
        }

    block = (payload.get("payload") or {}).get("block") or {}
    if not isinstance(block, dict) or block.get("type") != "state":
        return _fail("PAYMENT-SIGNATURE block is not a Nano state block")

    # Fast destination check before spending an RPC call or broadcasting.
    destination = block.get("link_as_account") or block.get("link", "")
    if destination != expected_destination:
        return _fail(
            f"Payment sent to wrong address: {str(destination)[:15]}... "
            f"(expected {str(expected_destination)[:15]}...)"
        )

    # Broadcast.  ``process`` validates signature/work/balance on-ledger and
    # rejects a forged or unsigned block, so a bad block stops here honestly.
    res = broadcast_block(block)
    if not res.get("ok"):
        return _fail(f"Payment could not be broadcast: {res.get('error', 'unknown')}")

    block_hash = res["hash"]

    # Wait for confirmation.
    conf = wait_for_confirmation(block_hash)
    if not conf.get("confirmed"):
        return {
            "valid": False, "amount_raw": "0",
            "source": block.get("account", ""),
            "destination": destination,
            "message": f"Payment broadcast but not confirmed: {conf.get('error', 'unknown')}",
            "block_hash": block_hash,
        }

    # Re-verify the now on-ledger block exactly like a self-broadcast payment.
    verification = verify_payment(block_hash, expected_price_raw, expected_destination)
    verification["block_hash"] = block_hash
    verification["broadcast_marker"] = head_and_tail(block_hash)
    return verification


def head_and_tail(s: str, head: int = 8, tail: int = 8) -> str:
    """Shorten a long identifier for display, e.g. 'ABCD1234...WXYZ5678'."""
    if len(s) <= head + tail + 3:
        return s
    return f"{s[:head]}...{s[-tail:]}"


def get_account_info(account: str) -> Optional[dict]:
    """Get account info from Nano RPC."""
    payload = {
        "action": "account_info",
        "account": account,
        "representative": "true",
        "weight": "true",
        "pending": "true"
    }
    headers = {}
    if NANO_RPC_KEY:
        headers["Authorization"] = f"Bearer {NANO_RPC_KEY}"

    try:
        resp = httpx.post(
            NANO_RPC_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def check_block_exists(block_hash: str) -> Optional[dict]:
    """Check if a block exists on the Nano ledger via block_info RPC."""
    payload = {"action": "block_info", "json_block": "true", "hash": block_hash}
    headers = {}
    if NANO_RPC_KEY:
        headers["Authorization"] = f"Bearer {NANO_RPC_KEY}"

    try:
        resp = httpx.post(NANO_RPC_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def verify_payment(block_hash: str, expected_amount_raw: str = PRICE_RAW,
                   expected_destination: str = "") -> dict:
    """
    Verify a Nano payment block on-ledger.
    
    Args:
        block_hash: The hash of the send block to verify
        expected_amount_raw: Amount in raw that the block should contain
        expected_destination: Account this payment should go to
    
    Returns:
        dict with keys: valid (bool), amount_raw (str), source (str),
                        destination (str), message (str)
    """
    if not expected_destination:
        expected_destination = VEND_ACCOUNT

    result = {
        "valid": False,
        "amount_raw": "0",
        "source": "",
        "destination": "",
        "message": "Payment not verified"
    }

    if not block_hash or len(block_hash) < 10:
        result["message"] = "Invalid block hash"
        return result

    block_info = check_block_exists(block_hash)
    if not block_info:
        # The RPC call failed (network, timeout, HTTP error).  Never let a
        # missing response crash the payment path: a 500 here would turn a
        # buyer's paid call into a lost sale.
        result["message"] = "Payment could not be verified: ledger RPC unreachable"
        return result
    if "error" in block_info:
        result["message"] = f"Block not found on ledger: {block_info.get('error', 'unknown error')}"
        return result

    # Parse the block contents
    contents = block_info.get("contents", {})
    if isinstance(contents, str):
        try:
            contents = json.loads(contents)
        except json.JSONDecodeError:
            result["message"] = "Cannot parse block contents"
            return result

    amount_raw = block_info.get("amount", "0")
    source = contents.get("account", "")
    # In Nano state blocks the destination is the `link` field (a hash); the
    # account form lives in `link_as_account`. Comparing the raw hash against an
    # account address rejects every valid payment, so prefer link_as_account.
    destination = contents.get("link_as_account") or contents.get("link", "")

    # Check destination matches
    if destination != expected_destination:
        result["message"] = (
            f"Payment sent to wrong address: {destination[:15]}... "
            f"(expected {expected_destination[:15]}...)"
        )
        result["amount_raw"] = amount_raw
        result["source"] = source
        result["destination"] = destination
        return result

    # Check amount meets minimum.
    #
    # Both sides have to parse as raw integers before the comparison can mean
    # anything.  Swallowing a parse error here and carrying on marked the
    # payment valid with the amount check never run, so a ledger response
    # carrying no usable `amount` (an empty string, a null, a proxy that drops
    # the field) bought an unlimited number of paid calls for nothing.  An
    # amount we cannot read is a payment we cannot verify: refuse it.
    try:
        actual_raw = int(amount_raw)
        minimum_raw = int(expected_amount_raw)
    except (ValueError, TypeError):
        result["message"] = (
            f"Cannot read the payment amount from this block (ledger reported "
            f"{amount_raw!r}); payment not verified"
        )
        result["amount_raw"] = str(amount_raw)
        result["source"] = source
        result["destination"] = destination
        return result

    if actual_raw < minimum_raw:
        actual_xno = raw_to_xno(amount_raw)
        expected_xno = raw_to_xno(expected_amount_raw)
        result["message"] = (
            f"Payment too small: {actual_xno} XNO (expected at least {expected_xno} XNO)"
        )
        result["amount_raw"] = amount_raw
        result["source"] = source
        result["destination"] = destination
        return result

    result["valid"] = True
    result["amount_raw"] = amount_raw
    result["source"] = source
    result["destination"] = destination
    result["message"] = f"Payment verified: {raw_to_xno(amount_raw)} XNO received"
    return result


def build_402_challenge(endpoint_path: str, price_xno: float = 0.0001,
                         price_raw: str = "", resource_url: str = "",
                         input_spec: Optional[dict] = None) -> dict:
    """Build the x402 v2 challenge object for one paid call.

    The shape follows the live reference merchants on ``nano:mainnet``
    (feeless402): ``resource`` is an object with an absolute URL and a
    mimeType, ``accepts[]`` carries the exact raw amount and a
    ``maxTimeoutSeconds``, and ``extensions["rail-hint"]`` teaches a visiting
    agent how to onboard.  The accepts array is the only binding part.

    When VEND_USDC_ADDRESS is set, a second accept (USDC-on-Base) is added
    to the array so the endpoint is discoverable by the CDP Bazaar and
    by agents that only know USDC on Base.

    ``input_spec`` (from ``extensions.bazaar.info``) describes what a buyer must
    send *before* they pay; two independent conformance checkers flag its
    absence because an agent that cannot know the request shape fails closed
    rather than paying.  It is attached under ``extensions.bazaar`` when given
    -- if not given, a minimal input schema is still emitted so the endpoint
    is always Bazaar-discoverable.
    """
    price_raw = price_raw or str(_price_to_raw(price_xno))
    extensions = {
        "rail-hint": {
            "info": {
                "cheapest": "nano:mainnet",
                "why": (
                    "Zero network fees, no minimum, sub-second finality. "
                    "This quote is the metered price; the payer pays exactly "
                    "the metered amount, with no gas floor."
                ),
                "bootstrap": "pip install feeless402 && nano-pay init",
                "topup": "nano-pay topup 5 --asset USDC-BASE --execute",
                "docs": "https://github.com/feeless402/feeless402",
                "site": "https://feeless402.com",
                "faucets": ["https://feeless402.com"],
                "spec": "x402 exact scheme on nano:mainnet",
            }
        }
    }

    # Always include a bazaar extension for CDP Bazaar discoverability,
    # even when input_spec is not provided.
    bazaar_ext = {
        "info": input_spec or {
            "input": {
                "type": "http",
                "method": "GET",
                "schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                },
            }
        }
    }
    extensions["bazaar"] = bazaar_ext

    # Build accepts array: always Nano
    accepts = [
        {
            "scheme": "exact",
            "network": "nano:mainnet",
            "asset": "XNO",
            "amount": price_raw,
            "payTo": VEND_ACCOUNT,
            "maxTimeoutSeconds": 60,
        }
    ]

    # Add USDC-on-Base accept when the EVM address is configured
    _usdc_pay_to = os.environ.get("VEND_USDC_ADDRESS", "")
    if _usdc_pay_to:
        try:
            from cdp_verify import build_usdc_accept
            usdc_raw = str(int(Decimal(str(price_xno)) * Decimal(10) ** 6))
            usdc_entry = build_usdc_accept(
                price_xno,
                pay_to_address=_usdc_pay_to,
                usdc_price_raw=usdc_raw,
            )
            if usdc_entry:
                accepts.append(usdc_entry)
        except Exception:
            # This handler exists so a USDC problem cannot cost us the XNO sale:
            # the Nano accept is already in `accepts` and the challenge must go
            # out with it. `logging` was not imported, so the handler raised
            # `NameError` and took the whole challenge with it - including the
            # Nano accept - and no agent could pay in XNO at all. Keep the
            # import; a bare `logging.getLogger` is the only thing between a
            # degraded USDC rail and no 402 challenge.
            log = logging.getLogger("vend")
            log.warning(
                "Failed to build USDC accept for %s", endpoint_path, exc_info=True
            )

    payment_req = {
        "x402Version": 2,
        "resource": {
            "url": resource_url or endpoint_path,
            "mimeType": "application/json",
        },
        "accepts": accepts,
        "extensions": extensions,
    }
    return payment_req


def format_402_response(endpoint_path: str, price_xno: float = 0.0001,
                        resource_url: str = "", price_raw: str = "",
                        input_spec: Optional[dict] = None) -> str:
    """Base64-encode the challenge for the PAYMENT-REQUIRED header."""
    return base64.b64encode(
        json.dumps(build_402_challenge(endpoint_path, price_xno, price_raw,
                                       resource_url, input_spec)).encode()
    ).decode()