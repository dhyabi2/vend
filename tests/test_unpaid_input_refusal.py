"""A paid call that cannot be served must not consume the buyer's payment.

Reported on 2026-09-25 (vend issue #1) by a buyer who paid 0.0001 XNO for
``/api/v1/geoip`` without an ``ip`` parameter, got HTTP 400, and lost the
payment.  Every paid endpoint had the same ordering: ``require_payment``
redeemed the block (or debited the prepaid balance, or broadcast the buyer's
signed block) and only then did the handler check its required parameters.

These laws pin the order the other way round: the required parameters are
checked first, and a 400 for a missing one leaves the payment untouched, so
the same payment presented again with the parameter is served.

The four controls at the end must hold either way — the refusal must not cost
a good call, and a bare x402 discovery probe must still get its 402 challenge.

Run: python3 -m pytest tests/test_unpaid_input_refusal.py -v
"""

import base64
import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import store
import server

BLOCK = "7CA569DA40F715A186718B4958C4AECE87781A04430F55BC2ED50A7E99EFFDEC"
BUYER = "nano_1cniy53izw4ks1zqvgc9fbxnpf6x1dmr8mifcnzuxnn7g7y8z7krg5wjrga"
VEND_TEST_ACCOUNT = "nano_3qgmh14nwztqw4wmcdzy4xpqeejey68chx6nciczwn9abji7ihhum9qtpmdr"


@pytest.fixture
def db():
    """A fresh redemption store, so 'was this block spent' is really observed.

    ``store.DB_PATH`` is read by ``_connect()`` on every call, so pointing it
    at a temp file is enough; ``_INIT_DONE`` is reset so the tables are built
    there rather than assumed from an earlier import.
    """
    path = tempfile.mktemp(suffix=".sqlite3")
    old_path, old_init = store.DB_PATH, store._INIT_DONE
    store.DB_PATH, store._INIT_DONE = path, False
    store.init()
    try:
        yield store
    finally:
        store.DB_PATH, store._INIT_DONE = old_path, old_init


@pytest.fixture
def client():
    return TestClient(server.app)


def _good_verification(block_hash, price_raw, account):
    """What a confirmed on-ledger payment of the right amount looks like."""
    return {
        "valid": True,
        "amount_raw": server.PRICE_GEO_RAW,
        "source": BUYER,
        "message": "confirmed",
        "block_hash": block_hash,
    }


def _signed_payload():
    """A spec-compliant PAYMENT-SIGNATURE carrying an UNBROADCAST signed block.

    Vend acts as its own facilitator for this dialect: it broadcasts the block
    via RPC ``process``, which is the moment the buyer's money actually moves.
    """
    payload = {
        "x402Version": 2,
        "resource": {"url": "https://extract.paypercall.dev/api/v1/geoip",
                     "mimeType": "application/json"},
        "accepted": {
            "scheme": "exact", "network": "nano:mainnet", "asset": "XNO",
            "amount": server.PRICE_GEO_RAW, "payTo": VEND_TEST_ACCOUNT,
            "maxTimeoutSeconds": 60,
        },
        "payload": {"block": {
            "type": "state",
            "account": BUYER,
            "previous": "F4" * 32,
            "representative": BUYER,
            "balance": "0",
            "link": VEND_TEST_ACCOUNT.encode().hex(),
            "link_as_account": VEND_TEST_ACCOUNT,
            "signature": "3B" * 64,
            "work": "ffffffd2e1234567",
        }},
        "extensions": {},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ── The defect ────────────────────────────────────────────────────────


def test_a_paid_call_missing_a_required_parameter_does_not_redeem_the_block(db, client):
    with patch("server.verify_payment", side_effect=_good_verification):
        resp = client.get("/api/v1/geoip", headers={"X-PAYMENT": BLOCK})

    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"] == "ip parameter is required"
    assert body["payment_taken"] is False

    # The buyer's block was never spent, so it is still theirs to present.
    assert db.status_of(BLOCK) is None, (
        f"block was redeemed for a call that returned 400: status={db.status_of(BLOCK)!r}"
    )


def test_the_same_payment_is_served_when_the_parameter_is_supplied(db, client):
    """The remedy the buyer was promised: retry the same block with the parameter."""
    with patch("server.verify_payment", side_effect=_good_verification):
        first = client.get("/api/v1/geoip", headers={"X-PAYMENT": BLOCK})
        assert first.status_code == 400, first.text

        with patch("server.geoip_lookup", return_value={"ip": "8.8.8.8", "country": "US"}):
            second = client.get(
                "/api/v1/geoip", params={"ip": "8.8.8.8"},
                headers={"X-PAYMENT": BLOCK},
            )

    assert second.status_code == 200, (
        f"the same payment was refused on retry: {second.status_code} {second.text}"
    )
    assert second.json()["country"] == "US"
    assert db.status_of(BLOCK) == "delivered"


def test_a_signed_payment_missing_the_parameter_is_never_broadcast(db, client):
    """For the x402 'exact' dialect, broadcasting IS the money moving.

    A request we are going to refuse must not reach ``confirm_signature_payment``,
    which hands the buyer's signed block to the node's ``process``.
    """
    with patch("server.confirm_signature_payment") as broadcast:
        resp = client.get(
            "/api/v1/geoip",
            headers={"PAYMENT-SIGNATURE": _signed_payload()},
        )

    assert resp.status_code == 400, resp.text
    assert resp.json()["payment_taken"] is False
    broadcast.assert_not_called()


def test_a_prepaid_balance_is_not_debited_for_a_call_missing_the_parameter(db, client):
    db.top_up("D" * 64, BUYER, str(10**28))          # 0.01 XNO of credit
    before = db.balance_of(BUYER)

    resp = client.get("/api/v1/geoip", headers={"X-BALANCE": BUYER})

    assert resp.status_code == 400, resp.text
    assert db.balance_of(BUYER) == before, (
        f"balance was debited for a 400: {before} -> {db.balance_of(BUYER)}"
    )


def test_a_blank_parameter_counts_as_missing_and_still_costs_nothing(db, client):
    with patch("server.verify_payment", side_effect=_good_verification):
        resp = client.get(
            "/api/v1/geoip", params={"ip": "   "},
            headers={"X-PAYMENT": BLOCK},
        )

    assert resp.status_code == 400, resp.text
    assert db.status_of(BLOCK) is None


def test_the_first_missing_of_two_required_parameters_is_the_one_named(db, client):
    """``/api/v1/select`` needs both url and selector; the message must be usable."""
    with patch("server.verify_payment", side_effect=_good_verification):
        resp = client.get(
            "/api/v1/select", params={"url": "https://example.com"},
            headers={"X-PAYMENT": BLOCK},
        )

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"].startswith("selector parameter is required")
    assert db.status_of(BLOCK) is None


# ── Controls: these must hold with or without the fix ──────────────────


def test_a_bare_probe_with_no_payment_still_gets_the_402_challenge(db, client):
    """x402 discovery (x402scan, CDP Bazaar) probes with no params and no payment.

    It must meet the payment challenge, not a validation error — otherwise the
    endpoint drops out of the directories that send buyers.
    """
    resp = client.get("/api/v1/geoip")

    assert resp.status_code == 402, resp.text
    assert resp.json()["error"] == "payment_required"
    assert "PAYMENT-REQUIRED" in resp.headers


def test_an_unpaid_call_that_names_the_parameter_still_gets_402_not_400(db, client):
    """No payment attempted, so there is nothing to protect: quote, don't refuse.

    ``geoip_lookup`` is stubbed because this server grants a free trial to a
    call that carries input, and a trial call would otherwise reach the real
    lookup backend — which this container's network policy answers 403.  The
    law is about which gate answers, not about the backend.
    """
    with patch("server.geoip_lookup", return_value={"ip": "8.8.8.8", "country": "US"}):
        resp = client.get("/api/v1/geoip", params={"ip": "8.8.8.8"})

    assert resp.status_code in (200, 402), resp.text
    if resp.status_code == 402:
        assert resp.json()["error"] == "payment_required"
    # Whatever happened, it was not the new unpaid-input refusal.
    assert resp.json().get("payment_taken") is not False


def test_a_paid_call_with_the_parameter_is_served_and_the_block_is_spent(db, client):
    with patch("server.verify_payment", side_effect=_good_verification):
        with patch("server.geoip_lookup", return_value={"ip": "1.1.1.1", "country": "AU"}):
            resp = client.get(
                "/api/v1/geoip", params={"ip": "1.1.1.1"},
                headers={"X-PAYMENT": BLOCK},
            )

    assert resp.status_code == 200, resp.text
    assert resp.json()["country"] == "AU"
    assert db.status_of(BLOCK) == "delivered"
    assert "payment" in resp.json()


def test_replay_of_a_spent_block_is_still_refused(db, client):
    """The refusal above must not have weakened replay prevention."""
    with patch("server.verify_payment", side_effect=_good_verification):
        with patch("server.geoip_lookup", return_value={"ip": "1.1.1.1", "country": "AU"}):
            first = client.get(
                "/api/v1/geoip", params={"ip": "1.1.1.1"},
                headers={"X-PAYMENT": BLOCK},
            )
            assert first.status_code == 200, first.text
            second = client.get(
                "/api/v1/geoip", params={"ip": "1.1.1.1"},
                headers={"X-PAYMENT": BLOCK},
            )

    assert second.status_code == 402, second.text
    assert second.json()["error"] == "payment_already_redeemed"
