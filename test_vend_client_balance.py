"""Tests for vend-client X-BALANCE prepaid balance support.

These tests exercise the client's request-building logic deterministically by
mocking the httpx transport, so no network or real Nano funds are needed.
"""

import httpx
import pytest

import os
import sys

# Make vend_client importable from the source tree
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vend_client_src"))

from vend_client.client import VendClient, VendError


class MockTransport(httpx.MockTransport):
    """A MockTransport that records the request it received."""

    def __init__(self):
        self.last_request = None
        self.responses = []
        super().__init__(self._handler)

    def _handler(self, request):
        self.last_request = request
        if self.responses:
            return self.responses.pop(0)
        return httpx.Response(402, json={"error": "payment_required"})


def make_client(**kwargs):
    transport = MockTransport()
    client = VendClient(
        endpoints={
            "extract": "http://test/api/v1/extract",
            "check_link": "http://test/api/v1/check-link",
            "domain_info": "http://test/api/v1/domain-info",
            "web_search": "http://test/api/v1/web-search",
            "geoip": "http://test/api/v1/geoip",
            "nano_info": "http://test/api/v1/nano-info",
            "balance": "http://test/api/v1/balance",
            "top_up": "http://test/api/v1/balance/top-up",
        },
        timeout=5.0,
        **kwargs,
    )
    client._client = httpx.Client(transport=transport, timeout=5.0)
    return client, transport


# ── X-BALANCE header is sent on paid-style calls ────────────────────────

def test_call_sends_x_balance_header_when_balance_account_set():
    client, transport = make_client(balance_account="nano_abc123")
    transport.responses.append(httpx.Response(200, json={"ok": True, "price_xno": 0.0001}))
    result = client.extract("https://example.com")
    assert result["ok"] is True
    assert transport.last_request.headers.get("X-BALANCE") == "nano_abc123"


def test_call_defers_to_x_balance_even_with_wallet():
    """If a wallet AND a balance_account are both set, X-BALANCE wins."""
    client, transport = make_client(balance_account="nano_walletdecides")
    transport.responses.append(httpx.Response(200, json={"ok": True}))
    client.web_search("hello")
    assert transport.last_request.headers.get("X-BALANCE") == "nano_walletdecides"


def test_dry_run_does_not_send_x_balance():
    client, transport = make_client()  # no balance_account, no wallet
    transport.responses.append(httpx.Response(402, json={"error": "payment_required"}))
    result = client.geoip("8.8.8.8")
    assert result.get("_dry_run") is True
    assert transport.last_request.headers.get("X-BALANCE") is None


def test_insufficient_balance_marks_result():
    client, transport = make_client(balance_account="nano_low")
    transport.responses.append(httpx.Response(402, json={"error": "payment_required"}))
    result = client.geoip("8.8.8.8")
    assert result.get("_balance_insufficient") is True
    assert result.get("_dry_run") is None


# ── balance() ────────────────────────────────────────────────────────────

def test_balance_requires_balance_account():
    client, _ = make_client()
    with pytest.raises(VendError):
        client.balance()


def test_balance_returns_balance():
    client, transport = make_client(balance_account="nano_hasfunds")
    transport.responses.append(httpx.Response(200, json={
        "account": "nano_hasfunds",
        "balance_raw": "1000000000000000000000000",
        "balance_xno": "0.001",
    }))
    result = client.balance()
    assert result["balance_xno"] == "0.001"
    assert transport.last_request.url.path == "/api/v1/balance"
    assert transport.last_request.headers.get("X-BALANCE") == "nano_hasfunds"


def test_balance_handles_402():
    client, transport = make_client(balance_account="nano_empty")
    transport.responses.append(httpx.Response(402, json={"error": "payment_required"}))
    result = client.balance()
    assert "error" in result


# ── top_up() ────────────────────────────────────────────────────────────

def test_top_up_requires_balance_account():
    client, _ = make_client()
    with pytest.raises(VendError):
        client.top_up("nano_blockhash")


def test_top_up_posts_account_and_block():
    client, transport = make_client(balance_account="nano_topher")
    transport.responses.append(httpx.Response(200, json={
        "ok": True,
        "balance_xno": "0.005",
        "block_hash": "abc123",
    }))
    result = client.top_up("abc123")
    assert result["ok"] is True
    req = transport.last_request
    assert req.url.path == "/api/v1/balance/top-up"
    assert req.method.lower() == "post"
    body = req.read().decode()
    assert "nano_topher" in body
    assert "abc123" in body


def test_top_up_handles_duplicate():
    client, transport = make_client(balance_account="nano_topher")
    transport.responses.append(httpx.Response(409, json={"message": "already used"}))
    result = client.top_up("dupblock")
    assert result["error"] == "duplicate_topup"


def test_top_up_handles_402():
    client, transport = make_client(balance_account="nano_topher")
    transport.responses.append(httpx.Response(402, json={"error": "payment_required"}))
    result = client.top_up("noblock")
    assert "error" in result
