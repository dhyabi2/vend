"""Tests for prepaid balance system (store functions).

Each test gets a fresh temp DB via fixture that reloads the module.
Run: python3 -m pytest test_balance.py -v
"""

import os
import sys
import tempfile
import pytest


@pytest.fixture
def store():
    """Provide a fresh store module with a unique temp DB for each test."""
    db_path = tempfile.mktemp(suffix=".sqlite3")

    # Remove any cached store module
    for mod_name in list(sys.modules.keys()):
        if "store" in mod_name and mod_name not in ("store_health",):
            del sys.modules[mod_name]

    # Set env BEFORE re-importing
    os.environ["VEND_DB"] = db_path

    import store as s
    s.init()
    return s


def assert_int(raw: str) -> int:
    """Safely parse raw string to int."""
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    return int(raw)


# ── Top-up tests ──────────────────────────────────────────────────


def test_topup_creates_balance(store):
    result = store.top_up(
        "A" * 64, "nano_test1", "1000000000000000000000000"
    )  # 1 XNO
    assert result is True
    bal = store.balance_of("nano_test1")
    assert bal == 1000000000000000000000000


def test_topup_adds_to_existing(store):
    store.top_up("B" * 64, "nano_test1", "1000000000000000000000000")
    store.top_up("C" * 64, "nano_test1", "500000000000000000000000")
    bal = store.balance_of("nano_test1")
    assert bal == 1500000000000000000000000  # 1.5 XNO


def test_topup_rejects_duplicate_block(store):
    assert store.top_up("D" * 64, "nano_test1", "1000000000000000000000000") is True
    assert store.top_up("D" * 64, "nano_test2", "1000000000000000000000000") is False


def test_topup_rejects_same_block_to_any_account(store):
    assert store.top_up("E" * 64, "nano_a", "1000000000000000000000000") is True
    assert store.top_up("E" * 64, "nano_b", "1000000000000000000000000") is False


def test_balance_of_unknown(store):
    assert store.balance_of("nano_unknown") == 0


# ── Deduct tests ─────────────────────────────────────────────────


def test_deduct_balance_success(store):
    store.top_up("F" * 64, "nano_test1", "100000000000000000000000")  # 0.1 XNO
    assert store.deduct_balance("nano_test1", "100000000000000000000000") is True
    assert store.balance_of("nano_test1") == 0


def test_deduct_balance_insufficient(store):
    store.top_up("G" * 64, "nano_test1", "100000000000000000000000")
    assert store.deduct_balance("nano_test1", "200000000000000000000000") is False
    assert store.balance_of("nano_test1") == 100000000000000000000000


def test_deduct_unknown_account(store):
    assert store.deduct_balance("nano_nobody", "100000000000000000000000") is False


# ── History / list tests ──────────────────────────────────────────


def test_get_topup_history(store):
    store.top_up("H" * 64, "nano_test1", "1000000000000000000000000")
    store.top_up("I" * 64, "nano_test1", "2000000000000000000000000")
    h = store.get_topup_history("nano_test1", limit=5)
    assert len(h) == 2
    assert h[0]["block_hash"] == "I" * 64  # most recent first (autoinc)
    assert h[1]["block_hash"] == "H" * 64


def test_get_topup_history_empty(store):
    assert store.get_topup_history("nano_empty") == []


def test_get_all_balances(store):
    store.top_up("J" * 64, "nano_small", "100000000000000000000000")
    store.top_up("K" * 64, "nano_large", "500000000000000000000000")
    all_b = store.get_all_balances()
    assert len(all_b) == 2
    assert all_b[0]["account"] == "nano_large"  # sorted by balance desc
    assert all_b[1]["account"] == "nano_small"


# ── Existing APIs still work ──────────────────────────────────────


def test_redemption_still_works(store):
    assert store.redeem("L" * 64, endpoint="/test", source="nano_test1") is True
    assert store.redeem("L" * 64, endpoint="/test", source="nano_test1") is False
    assert store.count_redeemed() == 1
    assert store.count_distinct_payers() == 1


# ── Integration flows ─────────────────────────────────────────────


def test_topup_then_deduct(store):
    # Account starts at 0
    assert store.balance_of("nano_buyer") == 0

    # Top-up with 10 XNO
    TEN_XNO_RAW = "10000000000000000000000000"
    assert store.top_up("M" * 64, "nano_buyer", TEN_XNO_RAW) is True
    assert store.balance_of("nano_buyer") == int(TEN_XNO_RAW)

    # Deduct 2 calls at 0.0001 XNO each
    PRICE_RAW = "100000000000000000000000"
    assert store.deduct_balance("nano_buyer", PRICE_RAW) is True
    assert store.deduct_balance("nano_buyer", PRICE_RAW) is True
    expected = int(TEN_XNO_RAW) - 2 * int(PRICE_RAW)
    assert store.balance_of("nano_buyer") == expected

    # Insufficient deduction
    BIG = "99999999999999999999999999999999"
    assert store.deduct_balance("nano_buyer", BIG) is False
    assert store.balance_of("nano_buyer") == expected


def test_multiple_accounts_independent(store):
    assert store.top_up("N" * 64, "nano_a", "1000000000000000000000000") is True
    assert store.top_up("O" * 64, "nano_b", "2000000000000000000000000") is True
    assert store.balance_of("nano_a") == 1000000000000000000000000
    assert store.balance_of("nano_b") == 2000000000000000000000000
    store.deduct_balance("nano_a", "100000000000000000000000")
    assert store.balance_of("nano_a") == 900000000000000000000000
    assert store.balance_of("nano_b") == 2000000000000000000000000  # unchanged


def test_replay_prevention(store):
    assert store.top_up("P" * 64, "nano_buyer", "1000000000000000000000000") is True
    # Same block can be used for top_up OR redemption (different tables)
    assert store.redeem("P" * 64, endpoint="/test", source="nano_buyer") is True
    # But cannot redeem twice (same table UNIQUE)
    assert store.redeem("P" * 64, endpoint="/test", source="nano_buyer") is False
    # And cannot top-up twice (same table UNIQUE)
    assert store.top_up("P" * 64, "nano_buyer", "1000000000000000000000000") is False