#!/usr/bin/env bash
# Oracle L55 — Vend serves a valid APIs.json at /.well-known/apis.json and /apis.json.
cd /root/swarm-vend
set -uo pipefail
python3 - <<'PY' || exit 1
import json, urllib.request, sys
def check(path):
    try:
        d = json.load(urllib.request.urlopen("https://extract.paypercall.dev"+path, timeout=12))
    except Exception as e:
        print(f"FAIL: {path} -> {e}"); sys.exit(1)
    props = {p.get("type") for p in ((d.get("apis") or [{}])[0].get("properties") or [])}
    ok = d.get("name")=="Vend API Merchant" and {"OpenAPI","MCP","LLMSTxt"}.issubset(props) and ("x-l402" in props or "x402" in props)
    print(f"{path}: props={sorted(props)}")
    return ok
if not (check("/.well-known/apis.json") and check("/apis.json")):
    sys.exit(1)
print("L55_APISJSON_PASS")
PY
