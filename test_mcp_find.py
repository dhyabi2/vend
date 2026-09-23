"""Tests for the mcp-find paid endpoint: module behavior + route wiring.

The module calls the live agent-tools.cloud directory, so tests mock the
HTTP layer to be deterministic and offline-safe, then verify the route
level (402 on probe, param validation) through the server.
"""

import json
import asyncio
from unittest.mock import patch, MagicMock

# ── module-level tests (offline, mocked) ─────────────────────────────


@patch("mcp_find.httpx.Client")
def test_mcp_find_returns_matching_services(MockClient):
    """mcp_find returns parsed services from the directory JSON."""
    from mcp_find import mcp_find

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "count": 2,
        "services": [
            {
                "name": "Nano Scraper",
                "url": "https://nano.scraper/api",
                "description": "scrape pages",
                "category": "mcp",
                "chains": ["nano:mainnet"],
                "price_min": 0.001,
                "price_max": 0.001,
                "currency": "XNO",
                "x402_ok": True,
                "payto_payers_30d": 42,
                "tx_30d": 100,
                "health": "ok",
                "mcp_url": "https://nano.scraper/mcp",
            },
            {
                "name": "Base Tool",
                "url": "https://base.tool/api",
                "description": "base service",
                "category": "x402",
                "chains": ["base"],
                "price_min": 0.01,
                "price_max": 0.01,
                "x402_ok": True,
            },
        ],
    }

    mock_client_ctx = MockClient.return_value.__enter__.return_value
    mock_client_ctx.get.return_value = mock_resp

    result = mcp_find("scrape", limit=10)
    assert result.get("error") is None
    assert result["source"] == "agent-tools.cloud"
    assert result["result_count"] == 2
    assert result["results"][0]["name"] == "Nano Scraper"
    assert result["results"][0]["chains"] == ["nano:mainnet"]
    assert result["results"][0]["x402_ok"] is True


@patch("mcp_find.httpx.Client")
def test_mcp_find_filter_rail(MockClient):
    """filter_rail='nano' keeps only services whose chains include the nano scheme."""
    from mcp_find import mcp_find

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "services": [
            {"name": "A", "url": "u1", "chains": ["nano:mainnet"], "price_min": 0.1},
            {"name": "B", "url": "u2", "chains": ["base"], "price_min": 0.1},
            {"name": "C", "url": "u3", "chains": ["eip155:8453"], "price_min": 0.1},
        ]
    }

    mock_client_ctx = MockClient.return_value.__enter__.return_value
    mock_client_ctx.get.return_value = mock_resp

    result = mcp_find("pay", filter_rail="nano")
    names = [r["name"] for r in result["results"]]
    assert names == ["A"], f"expected only A, got {names}"


@patch("mcp_find.httpx.Client")
def test_mcp_find_source_failure_returns_empty(MockClient):
    """If the source raises, mcp_find returns an error dict (never crashes)."""
    from mcp_find import mcp_find

    mock_client_ctx = MockClient.return_value.__enter__.return_value
    mock_client_ctx.get.side_effect = Exception("network down")

    result = mcp_find("anything")
    assert result["error"] == "all discovery sources failed"
    assert result["result_count"] == 0


def test_mcp_find_empty_query():
    """An empty query is rejected with a clear error."""
    from mcp_find import mcp_find

    result = mcp_find("")
    assert result.get("error") == "query parameter is required"


@patch("mcp_find.httpx.Client")
def test_mcp_find_none_chains_does_not_crash(MockClient):
    """A service with chains=None does not crash the rail filter."""
    from mcp_find import mcp_find

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "services": [{"name": "N", "url": "u", "chains": None, "price_min": 0.1}]
    }
    mock_client_ctx = MockClient.return_value.__enter__.return_value
    mock_client_ctx.get.return_value = mock_resp

    result = mcp_find("x", filter_rail="nano")
    assert result["result_count"] == 0


# ── route-level tests (via server import) ────────────────────────────


def test_mcp_find_in_input_specs():
    """The endpoint is declared in endpoint_meta INPUT_SPECS (402 challenge input spec)."""
    from endpoint_meta import INPUT_SPECS

    assert "/api/v1/mcp-find" in INPUT_SPECS
    spec = INPUT_SPECS["/api/v1/mcp-find"]
    assert spec["method"] == "GET"
    assert "q" in spec["input"]["schema"]["required"]


def test_mcp_find_in_x402_manifest():
    """The endpoint is advertised in the x402 manifest with a Nano accepts entry."""
    from server import x402_manifest, VEND_ACCOUNT

    manifest = x402_manifest()
    resources = manifest["resources"]
    entry = next((r for r in resources if "mcp-find" in r["url"]), None)
    assert entry is not None, "mcp-find not in x402 manifest"
    assert entry["method"] == "GET"
    accepts = entry["accepts"]
    assert len(accepts) == 1
    assert accepts[0]["network"] == "nano:mainnet"
    assert accepts[0]["asset"] == "XNO"
    assert accepts[0]["payTo"] == VEND_ACCOUNT


def test_mcp_find_endpoint_decorated():
    """The route handler exists on the app and is registered as a GET path."""
    import server

    routes = [getattr(r, "path", None) for r in server.app.routes]
    assert "/api/v1/mcp-find" in routes
