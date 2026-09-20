#!/usr/bin/env python3
"""Probe the Vend MCP Streamable HTTP endpoint with a correct protocol session.

The MCP Streamable HTTP transport requires:
1. POST /mcp with {"jsonrpc":"2.0","id":1,"method":"initialize", ...}
   and NO Mcp-Session-Id header (session handshake).
2. Read Mcp-Session-Id from the response.
3. POST /mcp with tools/list, carrying the session id + Accept header.

This script performs the full handshake and lists the Vend MCP tools,
proving the endpoint works for real MCP clients.
"""
import json
import sys
import urllib.request

BASE = "https://extract.paypercall.dev/mcp"
HD = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

def post(body, headers=()):
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(),
                                 headers={**HD, **dict(headers)}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, resp, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e, e.read()

def parse(content):
    text = content.decode() if isinstance(content, bytes) else content
    # Streamable HTTP may return SSE (event: message\ndata: {...}) or raw JSON
    if "data:" in text:
        lines = text.replace("\r\n", "\n").splitlines()
        data_lines = []
        for l in lines:
            if l.startswith("data:"):
                data_lines.append(l[5:].strip())
        if data_lines:
            return [json.loads(d) for d in data_lines if d]
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        return [{"raw": text[:300]}]

# 1. Initialize
init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18",
                   "capabilities": {}, "clientInfo": {"name": "vend-probe", "version": "0.1"}}}
code, resp, content = post(init)
print(f"initialize: HTTP {code}")
sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
print(f"session id: {sid}")
msgs = parse(content)
for m in msgs:
    if m.get("result"):
        si = m["result"].get("serverInfo", {})
        print(f"server: {si.get('name')} v{si.get('version')}")
        print(f"protocolVersion: {m['result'].get('protocolVersion')}")
    elif m.get("error"):
        print(f"init error: {m['error']}")
        sys.exit(1)

if not sid:
    print("FAIL: no session id returned; MCP handshake broken")
    sys.exit(1)

# 2. tools/list within session
tool_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
code, resp, content = post(tool_req, headers={"Mcp-Session-Id": sid})
print(f"tools/list: HTTP {code}")
msgs = parse(content)
tools = None
for m in msgs:
    if m.get("result"):
        tools = m["result"].get("tools", [])
if tools is None:
    print("FAIL: no tools in response:", msgs)
    sys.exit(1)

print(f"MCP tools exposed: {len(tools)}")
for t in tools:
    print(f"  - {t.get('name')}: {t.get('description','')[:60]}")
print("MCP_PROBE_PASS")
