"""Discovery parity (issue #461): every door sells the same paid menu.

/.well-known/x402 is the one list. /openapi.json, /llms.txt and
/.well-known/agent-tools.json are derived from it, so the set of paid
/api/v1 paths must be identical on all four. The same comparison that
bin/deploy-parity.py makes against the LIVE hosts, run here in-process.

Run: .venv/bin/python -m pytest -q tests/test_discovery_parity.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

# payTo comes from NANO_AGENT_ACCOUNT (live: nano_1yo6c1t6...mnx7); every door
# must quote the same one the manifest does.
PAY_TO = server.VEND_ACCOUNT

API = re.compile(r"/api/v1/[A-Za-z0-9_/-]+")
client = TestClient(server.app)


def _x402():
    doc = client.get("/.well-known/x402").json()
    paid = {}
    for r in doc["resources"]:
        if r.get("accepts"):
            paid[API.search(r["url"]).group(0)] = r
    return paid


def _openapi_paid():
    doc = client.get("/openapi.json").json()
    out = set()
    for path, ops in doc["paths"].items():
        if any("x-payment-info" in op for op in ops.values()):
            out.add(path)
    return out, doc


def test_x402_manifest_is_the_whole_catalogue():
    paid = _x402()
    # Every endpoint with an input spec is sold, plus the POST top-up.
    assert set(server.INPUT_SPECS) <= set(paid)
    assert "/api/v1/balance/top-up" in paid
    for r in paid.values():
        for a in r["accepts"]:
            assert a["payTo"] == PAY_TO


def test_openapi_equals_x402():
    paid = _x402()
    got, doc = _openapi_paid()
    assert got == set(paid)
    api_paths = {p for p in doc["paths"] if p.startswith("/api/v1/")}
    assert api_paths == set(paid)
    for path, r in paid.items():
        assert r["method"].lower() in doc["paths"][path]


def test_llms_equals_x402():
    paid = _x402()
    text = client.get("/llms.txt").text
    assert "<!-- PAID-ENDPOINTS -->" not in text
    table = text.split("## Endpoints", 1)[1].split("\n\n", 2)[1]
    assert set(API.findall(table)) == set(paid)


def test_agent_tools_equals_x402():
    paid = _x402()
    doc = client.get("/.well-known/agent-tools.json").json()
    res = doc["x402"]["resources"]
    sold = {r["path"] for r in res if not r.get("free")}
    assert sold == set(paid)
    for r in res:
        if r.get("free"):
            continue
        assert r["pay_to"] == PAY_TO
        want = paid[r["path"]]["accepts"][0]["amount"]
        assert str(r["price_raw"]) == str(want)


def test_generated_openapi_carries_input_params():
    _, doc = _openapi_paid()
    op = doc["paths"]["/api/v1/select"]["get"]
    names = {p["name"] for p in op.get("parameters", [])}
    assert {"url", "selector"} <= names
    assert op["x-payment-info"]["protocols"] == [{"x402": {}}]
