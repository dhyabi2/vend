"""
Nano account intelligence — queries the Nano ledger via public RPC.

Returns structured account data (balance, representative, block count,
frontier, weight, pending) for any Nano account.  Leverages the
``get_account_info`` function already in ``nano_verify``.

Priced at 0.0005 XNO per call (covers the upstream RPC call cost
and provides significant value to agents checking Nano accounts).
"""

import logging
from nano_verify import get_account_info, raw_to_xno

log = logging.getLogger("vend.nano_info")

# ─── main entry ────────────────────────────────────────────────────────────


def nano_account_info(account: str) -> dict:
    """Look up Nano account intelligence.

    Args:
        account: Nano account address (nano_... or xrb_... prefix).

    Returns:
        dict with keys: account, balance, balance_xno, representative,
        block_count, frontier, weight, weight_xno, pending, pending_xno,
        or error on failure.
    """
    if not account or not account.strip():
        return {"error": "account parameter is required"}

    account = account.strip()

    # Validate basic Nano address format
    if not (account.startswith("nano_") or account.startswith("xrb_")):
        return {"error": "Invalid Nano address: must start with nano_ or xrb_"}

    result = get_account_info(account)
    if result is None:
        return {"error": "Nano RPC unreachable or returned no response"}
    if "error" in result:
        return {"error": result["error"]}

    # Build structured response
    balance_raw = result.get("balance", "0")
    pending_raw = result.get("pending", "0")
    weight_raw = result.get("weight", "0")

    return {
        "account": account,
        "frontier": result.get("frontier", ""),
        "open_block": result.get("open_block", ""),
        "representative": result.get("representative", ""),
        "block_count": result.get("block_count", "0"),
        "balance": balance_raw,
        "balance_xno": raw_to_xno(balance_raw),
        "pending": pending_raw,
        "pending_xno": raw_to_xno(pending_raw),
        "weight": weight_raw,
        "weight_xno": raw_to_xno(weight_raw),
        "modified_timestamp": result.get("modified_timestamp", "0"),
        "confirmation_height": result.get("confirmation_height", "0"),
        "confirmation_height_frontier": result.get("confirmation_height_frontier", ""),
    }
