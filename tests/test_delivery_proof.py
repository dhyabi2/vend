"""Tests for the delivery-attestation store functions.

Covers store.get_redemption: the database layer behind the
/api/v1/delivery-proof endpoint that lets any agent verify what a
paid call delivered (the most-wanted unmet x402 layer, hinge #82).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the store at a throwaway DB before importing it
_tmpdir = tempfile.mkdtemp()
os.environ["VEND_DB"] = os.path.join(_tmpdir, "test.sqlite3")

import store


def test_get_redemption_roundtrip():
    """A redemption recorded by redeem() is fully retrievable by get_redemption()."""
    bh = "A" * 64  # fake block hash
    store.redeem(bh, endpoint="/api/v1/geoip", amount_raw="100000000000000000000000000", source="nano_test")
    rec = store.get_redemption(bh)
    assert rec is not None
    assert rec["block_hash"] == bh
    assert rec["endpoint"] == "/api/v1/geoip"
    assert rec["amount_raw"] == "100000000000000000000000000"
    assert rec["source"] == "nano_test"
    assert rec["status"] == "claimed"
    assert rec["created_at"]
    print("PASS test_get_redemption_roundtrip")


def test_get_redemption_status_resolves():
    """After resolve(), the status reflects delivery outcome."""
    bh = "B" * 64
    store.redeem(bh, endpoint="/api/v1/extract", amount_raw="1", source="nano_test2")
    store.resolve(bh, "delivered")
    rec = store.get_redemption(bh)
    assert rec["status"] == "delivered"
    print("PASS test_get_redemption_status_resolves")


def test_get_redemption_unknown():
    """An unknown block hash returns None (endpoint returns 404)."""
    assert store.get_redemption("C" * 64) is None
    print("PASS test_get_redemption_unknown")


def test_get_redemption_after_failed():
    """A failed call is recorded as failed, so a buyer/seller can prove it was NOT delivered."""
    bh = "D" * 64
    store.redeem(bh, endpoint="/api/v1/web-search", amount_raw="1", source="nano_test3")
    store.resolve(bh, "failed")
    rec = store.get_redemption(bh)
    assert rec["status"] == "failed"
    print("PASS test_get_redemption_after_failed")


def test_get_redemption_case_insensitive():
    """A buyer who queries a paid block in a different case still finds it.
    (Hit live 2026-09-25: paid block stored upper-case, buyer queried lower-case
    '7ca569da...' and got a false 404 -> 'No payment found'.)"""
    bh = "0A1B" * 16  # 64 hex chars, mixed-known case
    store.redeem(bh, endpoint="/api/v1/geoip", amount_raw="100000000000000000000000000", source="nano_test4")
    # Query in lower case — must still resolve to the same (upper-stored) record
    rec = store.get_redemption(bh.lower())
    assert rec is not None, "lower-case block query must resolve"
    assert rec["block_hash"] == bh
    assert rec["endpoint"] == "/api/v1/geoip"
    # And the upper-case form still works
    assert store.get_redemption(bh.upper()) is not None
    print("PASS test_get_redemption_case_insensitive")


if __name__ == "__main__":
    test_get_redemption_roundtrip()
    test_get_redemption_status_resolves()
    test_get_redemption_unknown()
    test_get_redemption_after_failed()
    test_get_redemption_case_insensitive()
    print("\nAll delivery-proof store tests PASSED")
