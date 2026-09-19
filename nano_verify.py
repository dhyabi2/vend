"""Nano block verification via RPC (rpc.nano.to).
Verifies that a send block exists on-ledger with the expected amount and destination.
No facilitator — direct ledger check.
"""

import base64
import json
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

    # Check amount meets minimum
    try:
        if int(amount_raw) < int(expected_amount_raw):
            actual_xno = raw_to_xno(amount_raw)
            expected_xno = raw_to_xno(expected_amount_raw)
            result["message"] = (
                f"Payment too small: {actual_xno} XNO (expected at least {expected_xno} XNO)"
            )
            result["amount_raw"] = amount_raw
            result["source"] = source
            result["destination"] = destination
            return result
    except (ValueError, TypeError):
        pass

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