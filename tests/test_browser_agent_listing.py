"""The browser agent is advertised only where its gateway runs (VEND_BROWSER_AGENT=1), and then on every door.

The flag is read at import, so each case runs in its own interpreter.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = r"""
import asyncio, json, re
from fastapi.testclient import TestClient
import server, vend_mcp
c = TestClient(server.app)
m = c.get("/.well-known/x402").json()
entry = [r for r in m["resources"] if r["url"].endswith("/api/v1/browser-agent")]
tools = [t.name for t in asyncio.run(vend_mcp.create_server().list_tools())]
print("RESULT" + json.dumps({
    "manifest": len(entry),
    "amount": entry[0]["accepts"][0]["amount"] if entry else None,
    "pay_to_matches": entry[0]["accepts"][0]["payTo"] == server.VEND_ACCOUNT if entry else None,
    "last_is_topup": m["resources"][-1]["url"].endswith("/api/v1/balance/top-up"),
    "openapi": "/api/v1/browser-agent" in c.get("/openapi.json").json()["paths"],
    "llms": "/api/v1/browser-agent" in c.get("/llms.txt").text,
    "agent_tools": "/api/v1/browser-agent" in c.get("/.well-known/agent-tools.json").text,
    "mcp": sorted(t for t in tools if t.startswith("browser_agent")),
}))
"""


def probe(flag):
    env = dict(os.environ, NANO_AGENT_ACCOUNT="nano_3z335ug5oz6sxfgcfz3kdqdrgn5otx7ht3epuc3kuimka6hc59xqem1jrzqy",
               VEND_DB=os.path.join(ROOT, ".pytest-browser-agent.sqlite3"))
    env.pop("VEND_BROWSER_AGENT", None)
    if flag:
        env["VEND_BROWSER_AGENT"] = "1"
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    line = [l for l in out.stdout.splitlines() if l.startswith("RESULT")]
    assert line, out.stderr[-2000:]
    return json.loads(line[0][6:])


def test_not_advertised_without_the_gateway():
    r = probe(False)
    assert r["manifest"] == 0 and not r["openapi"] and not r["llms"] and not r["agent_tools"] and r["mcp"] == []


def test_advertised_on_every_door_with_the_gateway():
    r = probe(True)
    assert r["manifest"] == 1 and r["openapi"] and r["llms"] and r["agent_tools"]
    assert r["amount"] == str(5 * 10**28)          # 0.05 XNO, from 1 XNO = 10^30 raw
    assert r["pay_to_matches"] and r["last_is_topup"]
    assert r["mcp"] == ["browser_agent", "browser_agent_status"]
