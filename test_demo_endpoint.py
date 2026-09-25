"""Test the free demo endpoint (/api/v1/demo).

Guards the demo contract this branch ships (2026-09-24): /api/v1/demo serves
honest inline SAMPLE data (200) for every advertised type, decoupled from the
per-IP free-trial pool.

Why this replaces the older 307-trial-redirect contract (which main shipped
2026-09-23): a redirect into the paid endpoint burned the per-IP free-trial
budget on the real endpoint, and once the shared trial was spent the advertised
'free preview' became a 402 paywall (join:#114, re-confirmed live as join:#304).
Serving samples holds the docs promise for a stranger on ANY shared/corporate IP
and never consumes trial budget.

The contract is honest when:

  - every advertised type answers 200 with a non-empty sample payload;
  - the body carries price_xno and endpoint so an agent can decide whether the
    real output is worth paying for;
  - x402_required is false (it is a free preview, never a paywall);
  - no type returns 307/402/404/5xx.
"""
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.testclient import TestClient
from server import app

client = TestClient(app)

# Every type the landing page / llms.txt advertises via the demo.
DEMO_TYPES = [
    "extract", "check-link", "batch-status", "status", "domain-info",
    "web-search", "geoip", "nano-info", "youtube-transcript", "screenshot",
    "render", "select", "links", "meta", "table", "pdf-extract", "mcp-find",
    "ai-jobs", "wiki-summary", "arxiv-paper", "hn-news", "address-verdict",
]


def test_demo_serves_sample_data_for_every_type():
    """The demo must answer 200 with a sample payload for every advertised
    type — a 307/402/404/5xx here is a buyer-journey defect."""
    for t in DEMO_TYPES:
        r = client.get(f"/api/v1/demo?type={t}")
        assert r.status_code == 200, (
            f"demo type={t} returned {r.status_code}, expected 200 sample data")
        body = r.json()
        assert body.get("demo") is True, f"demo type={t} missing demo:true"
        assert body.get("x402_required") is False, (
            f"demo type={t} is a paywall, expected free preview")
        assert body.get("sample"), f"demo type={t} missing sample payload"
        # An agent must be able to decide whether the real call is worth paying.
        assert body.get("price_xno") is not None, (
            f"demo type={t} missing price_xno")
        assert body.get("endpoint") == f"/api/v1/{t}", (
            f"demo type={t} wrong endpoint field")


def test_demo_never_paywalls_on_shared_ip():
    """The demo must not depend on the free-trial pool: even with the trial
    exhausted for the calling IP, the preview still serves sample data. This is
    the join:#114/#304 regression the inline-sample contract fixes."""
    for t in ("extract", "geoip", "nano-info", "pdf-extract"):
        r = client.get(f"/api/v1/demo?type={t}")
        assert r.status_code == 200, (
            f"demo type={t} returned {r.status_code} — free preview became a paywall")
        assert r.json().get("price_xno") is not None


def test_demo_does_not_redirect():
    """The demo is a 200 sample response, never a 307 into the paid endpoint."""
    r = client.get("/api/v1/demo", follow_redirects=False)
    assert r.status_code == 200, "demo must answer 200 inline samples, not a redirect"


def test_demo_rejects_an_unknown_type_honestly():
    """An unrecognised demo type must not be silently mislabelled as the extract
    sample: telling a buyer an endpoint that does not exist is real, and quoting
    a price and extract's output for it, is a lie the old .get() fallback told.
    It must answer 400 with the valid list (review-block on #333)."""
    r = client.get("/api/v1/demo?type=summarize")
    assert r.status_code == 400, (
        f"unknown demo type must be refused, got {r.status_code}")
    body = r.json()
    assert body.get("error") == "unknown demo type", body
    assert body.get("valid") == sorted(DEMO_TYPES), body
    # a path-traversal-looking value must not be echoed into endpoint either
    r2 = client.get("/api/v1/demo?type=..%2F..%2Fetc%2Fpasswd")
    assert r2.status_code == 400 and "valid" in r2.json(), r2.text
    # and a real type still answers 200
    assert client.get("/api/v1/demo?type=select").status_code == 200
