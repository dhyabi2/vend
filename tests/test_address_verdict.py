"""Tests for the Nano address-verdict module.

Mocks the public-RPC HTTP calls (no network dependency) to test the pure
classification logic deterministically across every verdict label, plus edge
cases: invalid addresses, unreachable RPC, and not-found accounts. A live
smoke test verifies the real RPC path and skips gracefully if unreachable.
"""

import os
import sys
import time
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import address_verdict as av

# ── Helpers ────────────────────────────────────────────────────────────────


def _mock_rpc(account_info, history):
    """Patch av._rpc to return the given account_info / account_history payloads.

    account_info: dict or None (None = RPC unreachable / transport error).
    history: dict with a 'history' list of blocks, or None.
    """
    def fake(payload):
        action = payload.get("action")
        if action == "account_info":
            return account_info
        if action == "account_history":
            return history
        return None
    return mock.patch.object(av, "_rpc", side_effect=fake)


def _block(btype, amount_raw, ts, account=None):
    blk = {"type": btype, "amount": str(amount_raw),
           "local_timestamp": str(ts)}
    if account is not None:
        blk["account"] = account
    return blk


# A real-ish account_info payload (values in raw).
INFO_ACTIVE = {
    "frontier": "A" * 64,
    "balance": "500000000000000000000000000000",  # 0.5 XNO
    "receivable": "100000000000000000000000000000",  # 0.1 XNO
    "block_count": "5",
    "representative": "nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou",
}
INFO_DUST = {
    "frontier": "B" * 64,
    "balance": "1000000000000000000000",  # 0.000001 XNO
    "receivable": "0",
    "block_count": "1",
    "representative": "nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou",
}
INFO_HIGH = {
    "frontier": "C" * 64,
    "balance": "5000000000000000000000000000000",  # 5 XNO
    "receivable": "0",
    "block_count": "8",
    "representative": "nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou",
}
INFO_NOT_FOUND = {"error": "Account not found"}

NOW = int(time.time())


# ── Format validation ───────────────────────────────────────────────────────

def test_invalid_address():
    res = av.address_verdict("not_an_address", now=NOW)
    assert res["address_valid"] is False
    assert res["label"] == "invalid_address"


def test_empty_address():
    res = av.address_verdict("", now=NOW)
    assert res["address_valid"] is False


def test_valid_format_check():
    assert av.is_valid_account("nano_1111111111111111111111111111111111111111111111111111hifc8npp")
    assert not av.is_valid_account("nano_short")


# ── RPC edge cases ─────────────────────────────────────────────────────────

def test_rpc_unreachable():
    with _mock_rpc(None, None):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["status"] == "unreachable"
    assert res["label"] == "unreachable"
    assert res["explanation"]  # honest no-verdict message


def test_not_found():
    with _mock_rpc(INFO_NOT_FOUND, None):
        res = av.address_verdict("nano_33t8h9z2t4c4nnds4qs3nws1kwz7zwt3x3kf1wz7zwt3x3kf1wz7hifc8npp-x", now=NOW)
    # not_found is decided by account_info lacking a frontier, not format
    with _mock_rpc(INFO_NOT_FOUND, None):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["on_ledger"] is False
    assert res["status"] == "not_found"
    assert res["label"] == "not_found"


# ── Classification labels ──────────────────────────────────────────────────

def test_not_found_clean():
    with _mock_rpc(INFO_NOT_FOUND, None):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "not_found"


def test_dust():
    # On ledger, trivial value ever received -> dust
    hist = {"history": [_block("receive", "1000000000000000000000", NOW - 100, account="nano_sender1")]}
    with _mock_rpc(INFO_DUST, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "dust", res
    assert res["on_ledger"] is True


def test_high_value_balance():
    hist = {"history": [_block("receive", "1000000000000000000000000000000", NOW - 100, account="nano_sender1")]}
    with _mock_rpc(INFO_HIGH, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "high_value", res
    assert res["signals"]["balance_xno"] == "5.000000"


def test_active_recent_receives():
    # Some value, recent activity -> active
    hist = {"history": [
        _block("receive", "200000000000000000000000000000", NOW - 50, account="nano_s1"),
        _block("receive", "300000000000000000000000000000", NOW - 100, account="nano_s2"),
        _block("send", "100000000000000000000000000000", NOW - 120),
    ]}
    info = dict(INFO_ACTIVE)
    with _mock_rpc(info, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "active", res
    assert res["signals"]["distinct_senders"] == 2
    assert res["signals"]["receive_count"] == 2
    assert res["signals"]["send_count"] == 1


def test_inactive_old_activity():
    # Has held value but no activity for > 90 days -> inactive
    hist = {"history": [_block("receive", "200000000000000000000000000000", NOW - 100 * 24 * 3600,
                               account="nano_s1")]}
    with _mock_rpc(INFO_ACTIVE, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "inactive", res


def test_wash_likely():
    # High receive volume but ~nothing retained -> wash_likely
    info = {
        "frontier": "D" * 64,
        "balance": "0",
        "receivable": "0",
        "block_count": "30",
        "representative": "nano_1stofnrxuz3cai7ze75o174bpm7scwj9jn3nxsn8ntzg784jf1gzn1jjdkou",
    }
    # 30 receives each of ~1 XNO, but account retains 0
    hist = {"history": [
        _block("receive", str(av.RAW_PER_XNO), NOW - 1000 - i * 10, account=f"nano_src{i}")
        for i in range(30)
    ]}
    with _mock_rpc(info, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    assert res["label"] == "wash_likely", res


def test_signals_report_sanely():
    hist = {"history": [
        _block("receive", "200000000000000000000000000000", NOW - 60, account="nano_s1"),
        _block("receive", "300000000000000000000000000000", NOW - 30, account="nano_s1"),
    ]}
    with _mock_rpc(INFO_ACTIVE, hist):
        res = av.address_verdict("nano_1111111111111111111111111111111111111111111111111111hifc8npp", now=NOW)
    sig = res["signals"]
    # total received 0.2+0.3 = 0.5 XNO
    assert res["label"] in ("active", "high_value")
    assert sig["distinct_senders"] == 1
    assert sig["receive_count"] == 2
    assert sig["total_received_xno"] == "0.500000"


# ── Live smoke test ────────────────────────────────────────────────────────

def test_live_smoke():
    """Real RPC call against the swarm treasury; skips if RPC is unreachable."""
    res = av.address_verdict("nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7", now=NOW)
    if res["status"] in ("unreachable",):
        print(f"SKIP live smoke (RPC unreachable): {res.get('explanation')}")
        return
    assert res["on_ledger"] is True
    assert res["label"] in ("high_value", "active", "inactive")
    assert res["signals"]["block_count"] is not None
    print(f"PASS live smoke: label={res['label']} balance={res['signals'].get('balance_xno')}")


if __name__ == "__main__":
    test_invalid_address()
    test_empty_address()
    test_valid_format_check()
    test_rpc_unreachable()
    test_not_found()
    test_not_found_clean()
    test_dust()
    test_high_value_balance()
    test_active_recent_receives()
    test_inactive_old_activity()
    test_wash_likely()
    test_signals_report_sanely()
    test_live_smoke()
    print("\nAll address_verdict module tests PASSED")
