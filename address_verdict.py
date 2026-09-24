"""
Nano on-chain address verdict for Vend.

Answers one question a buyer agent asks before it signs an x402 payment
toward a ``payTo`` account: *is this address real? has it actually held
value or been paid before, or is it a freshly-derived dust/wash account?*

The verdict is computed ONLY from observable, on-ledger data fetched over a
public Nano RPC (``account_info`` + ``account_history``).  No facilitator,
no index, no private data.  It never claims to know an account's human
intent or provenance; it reports the signals the ledger shows and a
conservative, data-grounded label with a confidence note.

Signals used:
  balance / receivable (pending balance)
  block_count, and send vs receive counts from history
  distinct senders it has received from, total received, largest inflow
  age (oldest history block) and recency (newest activity)
  a wash heuristic: high block volume with near-zero retained value

Verdict labels (honest, never a claim of intent):
  not_found    - the address is not on the ledger (no blocks at all)
  dust         - on ledger but has received only trivial value
  active       - newly active / modest real inflows
  high_value   - meaningful balance or cumulative inflow
  wash_likely  - high volume, near-zero net value retained (gaming heuristic)
  inactive     - on ledger but no recent activity

Priced at 0.0001 XNO per call (matches the sub-cent verdict floor).
"""

import json
import time

import httpx

# Public Nano RPC — the same one Vend's payment verification already trusts.
NANO_RPC_URL = "https://rpc.nano.to"

# Bounded fetch on history: enough to characterise an account without letting
# a hostile high-volume account blow up the call.  -1 asks for the full set on
# the RPC side, but we cap how many we actually inspect client-side.
HISTORY_FETCH_COUNT = "-1"
MAX_INSPECT = 2000
MAX_BYTES = 2 * 1024 * 1024
_TIMEOUT = 12
_UA = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"

# Raw -> XNO: 1 XNO == 10^30 raw.
RAW_PER_XNO = 10 ** 30

# Value thresholds (in XNO) for the conservative dust / high-value cutoffs.
# Chosen far below what a real paid service holds, so we never mislabel a
# genuine small seller as dust-honest while still flagging true dust.
DUST_XNO = 0.001
HIGH_VALUE_XNO = 1.0
# Wash heuristic: a volume account that retains essentially none of what it
# moved.  If this fraction of received value remains as balance+receivable,
# and there are many blocks, treat it as wash_likely.
WASH_RETAIN_FRACTION = 0.01
WASH_MIN_BLOCKS = 10
# "Inactive": no on-chain activity newer than this (seconds).
INACTIVE_AGE_S = 90 * 24 * 3600  # 90 days


def _xno(raw) -> str:
    try:
        return f"{int(raw) / RAW_PER_XNO:.6f}"
    except (ValueError, TypeError):
        return "unknown"


def is_valid_account(account) -> bool:
    """Loose Nano address-format check (nano_/xrb_ prefix, plausible length)."""
    if not isinstance(account, str):
        return False
    s = account.strip()
    if not (s.startswith("nano_") or s.startswith("xrb_")):
        return False
    # Base32 nano address body is 60 chars after the prefix; be tolerant but
    # require a plausible non-trivial length.
    body = s.split("_", 1)[1]
    return 50 <= len(body) <= 65


def _rpc(payload: dict):
    """POST a JSON action to the public Nano RPC, return parsed dict or None."""
    try:
        resp = httpx.post(
            NANO_RPC_URL,
            json=payload,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _account_info(account: str):
    return _rpc({
        "action": "account_info",
        "account": account,
        "representative": "true",
        "weight": "true",
        "pending": "true",
    })


def _account_history(account: str):
    return _rpc({
        "action": "account_history",
        "account": account,
        "count": HISTORY_FETCH_COUNT,
    })


def _signal_counts(history: list) -> dict:
    """Derive sender/volume signals from the raw history list (newest first)."""
    send_count = receive_count = 0
    total_received_raw = 0
    largest_inflow_raw = 0
    senders = set()
    first_ts = None
    last_ts = None
    for blk in history[:MAX_INSPECT]:
        btype = blk.get("type")
        amount_raw = blk.get("amount", "0")
        try:
            amount = int(amount_raw)
        except (ValueError, TypeError):
            amount = 0
        ts = blk.get("local_timestamp")
        try:
            it = int(ts)
        except (ValueError, TypeError):
            it = None
        if btype == "receive":
            receive_count += 1
            total_received_raw += amount
            if amount > largest_inflow_raw:
                largest_inflow_raw = amount
            src = blk.get("account")
            if src:
                senders.add(src)
        elif btype == "send":
            send_count += 1
        if it is not None:
            if first_ts is None or it < first_ts:
                first_ts = it
            if last_ts is None or it > last_ts:
                last_ts = it
    return {
        "send_count": send_count,
        "receive_count": receive_count,
        "distinct_senders": len(senders),
        "total_received_xno": _xno(total_received_raw),
        "largest_inflow_xno": _xno(largest_inflow_raw),
        "first_seen_ts": first_ts,
        "last_activity_ts": last_ts,
    }


def _verdict_label(info: dict, sig: dict, total_received_raw: int, now: int) -> str:
    """Return a conservative label from the observable signals."""
    try:
        balance_raw = int(info.get("balance", "0"))
    except (ValueError, TypeError):
        balance_raw = 0
    try:
        receivable_raw = int(info.get("receivable", info.get("pending", "0")))
    except (ValueError, TypeError):
        receivable_raw = 0
    retained = balance_raw + receivable_raw
    total_received = max(total_received_raw, 1)

    # Wash heuristic: a lot of receive volume but almost none retained.
    block_count = info.get("block_count", "0")
    try:
        blocks = int(block_count)
    except (ValueError, TypeError):
        blocks = 0
    if (
        blocks >= WASH_MIN_BLOCKS
        and retained / total_received < WASH_RETAIN_FRACTION
        and total_received >= int(RAW_PER_XNO)  # at least ~1 XNO moved through
    ):
        return "wash_likely"

    balance_xno = balance_raw / RAW_PER_XNO
    receivable_xno = receivable_raw / RAW_PER_XNO
    received_xno = total_received_raw / RAW_PER_XNO

    if received_xno < DUST_XNO and balance_xno < DUST_XNO:
        return "dust"

    if balance_xno >= HIGH_VALUE_XNO or received_xno >= HIGH_VALUE_XNO:
        return "high_value"

    # Inactive: on ledger, some value ever, but no recent activity.
    last = sig.get("last_activity_ts")
    if last is not None and (now - int(last)) > INACTIVE_AGE_S:
        return "inactive"

    return "active"


def address_verdict(account: str, now: int = None) -> dict:
    """Return an on-ledger trust verdict for a Nano address.

    Args:
        account: Nano address (nano_/xrb_ prefix).
        now: unix time for recency decisions (defaults to time.time()).

    Returns:
        dict with keys: account, address_valid, on_ledger, status, label,
        signals {…}, explanation, or error on transport failure.
    """
    if now is None:
        now = int(time.time())
    account = (account or "").strip()
    if not is_valid_account(account):
        return {
            "account": account,
            "address_valid": False,
            "on_ledger": False,
            "status": "invalid_address",
            "label": "invalid_address",
            "signals": {},
            "explanation": "Not a valid Nano address (must start nano_ or xrb_).",
        }

    info = _account_info(account)
    if info is None:
        return {
            "account": account, "address_valid": True, "on_ledger": False,
            "status": "unreachable", "label": "unreachable", "signals": {},
            "explanation": "Nano RPC unreachable or returned no response. "
                           "No verdict issued (not paid-for work).",
        }
    if "error" in info or not info.get("frontier"):
        return {
            "account": account, "address_valid": True, "on_ledger": False,
            "status": "not_found", "label": "not_found", "signals": {},
            "explanation": "Not found on the Nano ledger (no blocks). This "
                           "address has never transacted.",
        }

    hist = _account_history(account)
    history = []
    if isinstance(hist, dict):
        history = hist.get("history", []) or []

    sig = _signal_counts(history)

    # Recompute cumulative received and largest inflow in raw from history so
    # the label and emitted signals agree exactly.
    received_raw = 0
    largest_raw = 0
    for blk in history[:MAX_INSPECT]:
        if blk.get("type") == "receive":
            try:
                a = int(blk.get("amount", "0"))
            except (ValueError, TypeError):
                a = 0
            received_raw += a
            if a > largest_raw:
                largest_raw = a

    sig["total_received_xno"] = _xno(received_raw)
    sig["largest_inflow_xno"] = _xno(largest_raw)

    label = _verdict_label(info, sig, received_raw, now)

    try:
        balance_xno = _xno(info.get("balance", "0"))
    except Exception:
        balance_xno = "unknown"
    try:
        receivable_xno = _xno(info.get("receivable", info.get("pending", "0")))
    except Exception:
        receivable_xno = "unknown"

    signals = {
        "block_count": info.get("block_count", "0"),
        "balance_xno": balance_xno,
        "receivable_xno": receivable_xno,
        "send_count": sig["send_count"],
        "receive_count": sig["receive_count"],
        "distinct_senders": sig["distinct_senders"],
        "total_received_xno": sig["total_received_xno"],
        "largest_inflow_xno": sig["largest_inflow_xno"],
        "account_age_s": (now - int(sig["first_seen_ts"])) if sig.get("first_seen_ts") else None,
        "last_activity_s_ago": (now - int(sig["last_activity_ts"])) if sig.get("last_activity_ts") else None,
        "representative": info.get("representative", ""),
        "frontier": info.get("frontier", ""),
    }

    explanation = {
        "not_found": "Address is not on the ledger — it has never transacted.",
        "dust": "On ledger but has held only trivial value; treat as low-trust.",
        "active": "On ledger with real (modest) value history and recent activity.",
        "high_value": "On ledger with meaningful balance or cumulative inflow.",
        "wash_likely": "High block volume with near-zero retained value — "
                       "consistent with a wash/volume pattern.",
        "inactive": "On ledger with some history but no recent activity.",
        "invalid_address": "Not a valid Nano address.",
        "unreachable": "RPC unreachable; no verdict issued.",
    }.get(label, "Verdict issued from on-ledger signals.")

    return {
        "account": account,
        "address_valid": True,
        "on_ledger": True,
        "status": "ok",
        "label": label,
        "signals": signals,
        "explanation": explanation,
    }
