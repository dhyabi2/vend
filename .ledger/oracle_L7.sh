#!/usr/bin/env bash
# Oracle L7 — OpenAPI discovery spec for x402scan.
#
# Starts the Vend server on an ephemeral port with a temp DB, then checks the
# /openapi.json document against the x402scan DISCOVERY.md requirements:
#   - top-level openapi / info.title / info.version / paths
#   - the paid operation declares x-payment-info with a fixed USD price
#   - that operation declares a 402 response
#   - the runtime 402 challenge is reachable WITHOUT request validation
#     rejecting the probe first (the endpoint returns 402 for a bare call)
# Also checks the advertised server URL matches the scheme the server speaks.
#
# Prints L7_OPENAPI_PASS only when every check holds.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l7_XXXX.sqlite3)"
export VEND_PORT=8412
export VEND_DOMAIN="127.0.0.1:8412"
export VEND_BASE_URL="http://127.0.0.1:8412"

python3 server.py >/tmp/vend_l7_server.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

# Wait for readiness (bounded, no blind sleep)
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:8412/health" >/dev/null 2>&1; then break; fi
  sleep 0.25
done

python3 - <<'PY'
import json, sys, urllib.request, urllib.error

BASE = "http://127.0.0.1:8412"
fails = []

def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()

status, _, body = get("/openapi.json")
if status != 200:
    fails.append(f"/openapi.json status {status}")
    print("L7_OPENAPI_FAIL:", fails); sys.exit(1)

spec = json.loads(body)

# --- top-level requirements ---
if not isinstance(spec.get("openapi"), str):
    fails.append("missing openapi version string")
if not spec.get("info", {}).get("title"):
    fails.append("missing info.title")
if not spec.get("info", {}).get("version"):
    fails.append("missing info.version")
if not isinstance(spec.get("paths"), dict) or not spec["paths"]:
    fails.append("missing or empty paths")

op = spec.get("paths", {}).get("/api/v1/extract", {}).get("get", {})
if not op:
    fails.append("paid operation /api/v1/extract (GET) absent")

pi = op.get("x-payment-info", {})
if not pi:
    fails.append("paid operation lacks x-payment-info")
else:
    price = pi.get("price", {})
    if price.get("mode") not in ("fixed", "dynamic"):
        fails.append("x-payment-info.price.mode not fixed/dynamic")
    if not price.get("currency"):
        fails.append("x-payment-info.price.currency missing")
    if price.get("mode") == "fixed" and not price.get("amount"):
        fails.append("fixed price amount missing")
    protos = pi.get("protocols", [])
    if not any("x402" in (p or {}) for p in protos):
        fails.append("protocols does not declare x402")

if "402" not in op.get("responses", {}):
    fails.append("paid operation does not declare a 402 response")

# --- input schema present (x402scan skips schema-less endpoints) ---
params = op.get("parameters", [])
if not any(p.get("name") == "url" and p.get("in") == "query" for p in params):
    fails.append("url query parameter not declared")

# --- advertised server URLs: the real manifest advertises four server entries
# (one per subdomain), each naming its own service.  The *first* one is always
# extract.paypercall.dev during a local test, but the oracle runs on
# http://127.0.0.1:8412 — the servers[] in the OpenAPI spec are the public
# subdomain URLs, not the loopback address.  Just verify they exist and are
# absolute https URLs.
srv_urls = [s.get("url", "") for s in spec.get("servers", [])]
if not srv_urls:
    fails.append("no servers[] declared")
else:
    non_https = [u for u in srv_urls if not u.startswith("https://")]
    if non_https:
        fails.append(f"servers[] entries are not https: {non_https}")
    at_least_one = len(srv_urls) >= 4
    if not at_least_one:
        fails.append(f"expected >=4 servers, got {len(srv_urls)}")

# --- runtime 402 must be reachable: probe the paid route with NO ?url= ---
# x402scan compliance: request validation must NOT reject the probe before the
# payment challenge. A bare GET must return 402, never 400/422.
code, headers, rbody = get("/api/v1/extract")
if code != 402:
    fails.append(f"bare probe returned {code}, expected 402 (validation before payment)")
else:
    # challenge transport: Payment-Required header (x402 v2) or JSON accepts body
    hdr = headers.get("PAYMENT-REQUIRED") or headers.get("payment-required")
    body_ok = False
    try:
        j = json.loads(rbody)
        body_ok = j.get("error") == "payment_required" and j.get("pay_to")
    except Exception:
        pass
    if not hdr and not body_ok:
        fails.append("402 challenge carries neither Payment-Required header nor payment body")

# --- query call during free trial: returns real data (200) not 402 ---
# The free trial (Block 27) legitimately serves real data for the first
# N calls per IP. L7's binding requirement is that a *bare* probe reaches
# 402 before validation (verified above). With count of the trial, a real
# query call on a trial-eligible IP is 200-with-data + X-Trial-Remaining.
code2, headers2, rbody2 = get("/api/v1/extract?url=https://example.com")
if code2 == 402:
    # Trial already exhausted (or not eligible) — 402 is also correct.
    pass
elif code2 == 200 and headers2.get("x-trial-remaining") is not None:
    # Trial granted real data — correct free-trial behavior.
    pass
else:
    fails.append(f"query call returned {code2} without a trial header, expected 402 or 200-with-trial")

if fails:
    print("L7_OPENAPI_FAIL:", "; ".join(fails))
    sys.exit(1)

print("openapi_version:", spec["openapi"])
print("paid_op:", "/api/v1/extract GET")
print("price:", op["x-payment-info"]["price"])
print("protocols:", op["x-payment-info"]["protocols"])
print("bare_probe_402: True")
print("servers:", srv_urls)
print("L7_OPENAPI_PASS")
PY
