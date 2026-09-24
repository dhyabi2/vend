#!/usr/bin/env bash
# Oracle for L39 & L40 — one-call URL status endpoint + A2A agent card.
#
# L39: GET /api/v1/status returns 402 for a bare probe and one complete status
#      document for a real call (final status, redirect chain, TLS validity and
#      days-to-expiry, response time, content hash), and it is announced in every
#      discovery surface.
# L40: /.well-known/agent-card.json answers 200 with a conformant A2A agent card
#      naming the six skills and the Nano x402 rail with the treasury payTo.
#
# Runs against a private in-process server with a temp DB, so it proves the code
# in this repo, not whatever happens to be deployed.
#
# Prints L39_STATUS_PASS / L40_AGENTCARD_PASS (and STATUS_ORACLE_PASS at the end)
# only when the checks hold.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l39_XXXX.sqlite3)"
export VEND_PORT=8416
export VEND_DOMAIN="127.0.0.1:8416"
export VEND_BASE_URL="http://127.0.0.1:8416"

python3 server.py >/tmp/vend_l39_server.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:8416/health" >/dev/null 2>&1; then break; fi
  sleep 0.25
done

python3 - <<'PY'
import json, sys, urllib.request, urllib.error, hashlib

BASE = "http://127.0.0.1:8416"
fails = []

def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()

# ── L39: bare probe must answer 402 with the payment challenge ──────────────
st, hdrs, body = get("/api/v1/status")
if st != 402:
    fails.append(f"L39: bare /api/v1/status answered {st}, expected 402")
else:
    try:
        d = json.loads(body)
        res = d.get("resource")
        res_url = res.get("url") if isinstance(res, dict) else res
        if not res_url or not res_url.endswith("/api/v1/status"):
            fails.append(f"L39: 402 challenge resource is {res_url!r}")
        if not d.get("accepts"):
            fails.append("L39: 402 challenge carries no accepts[]")
    except Exception as e:
        fails.append(f"L39: 402 body is not the payment challenge JSON: {e}")

# ── L39: a real call returns one complete status document ───────────────────
st, hdrs, body = get("/api/v1/status?url=https://example.com")
if st != 200:
    fails.append(f"L39: real call answered {st}, expected 200 (trial or paid): {body[:200]}")
else:
    d = json.loads(body)
    for key in ("url", "final_url", "status_code", "ok", "reachable",
                "response_time_ms", "redirect_chain", "content_type",
                "content_length", "tls", "content_hash", "content", "checked_at"):
        if key not in d:
            fails.append(f"L39: status document is missing key {key!r}")
    if d.get("status_code") != 200:
        fails.append(f"L39: example.com status_code is {d.get('status_code')!r}, expected 200")
    if d.get("ok") is not True or d.get("reachable") is not True:
        fails.append(f"L39: ok={d.get('ok')!r} reachable={d.get('reachable')!r}, expected both True")
    h = d.get("content_hash") or ""
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        fails.append(f"L39: content_hash is not a sha256 hex digest: {h!r}")
    tls = d.get("tls") or {}
    if tls.get("valid") is not True:
        fails.append(f"L39: tls.valid is {tls.get('valid')!r} for an https URL")
    if not isinstance(tls.get("days_to_expiry"), int):
        fails.append(f"L39: tls.days_to_expiry is {tls.get('days_to_expiry')!r}, expected int")
    if not isinstance(d.get("response_time_ms"), int):
        fails.append(f"L39: response_time_ms is {d.get('response_time_ms')!r}, expected int")

    # content drift: calling again with the hash we just got must report unchanged
    st2, _, body2 = get(f"/api/v1/status?url=https://example.com&previous_hash={h}")
    if st2 != 200:
        fails.append(f"L39: drift call answered {st2}")
    else:
        d2 = json.loads(body2)
        if (d2.get("content") or {}).get("changed") is not False:
            fails.append(f"L39: same-hash drift call reported changed={(d2.get('content') or {}).get('changed')!r}, expected False")

# ── L39: bad input errors instead of charging ──────────────────────────────
st, _, body = get("/api/v1/status?url=notaurl")
if st == 200:
    d = json.loads(body)
    if not d.get("error"):
        fails.append("L39: invalid url answered 200 without an error field")

# ── L39: the endpoint is announced in every discovery surface ──────────────
for path in ("/.well-known/x402", "/.well-known/agent.json",
             "/.well-known/agent-tools.json", "/openapi.json",
             "/agents.txt", "/.well-known/ard.json"):
    st, _, body = get(path)
    if st != 200:
        fails.append(f"L39: {path} answered {st}")
    elif "/api/v1/status" not in body:
        fails.append(f"L39: {path} does not announce /api/v1/status")

if fails:
    print("L39_STATUS_FAIL:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("L39_STATUS_PASS: bare probe 402 with the endpoint's own resource URL; real call returns"
      " status/redirects/tls/docs/response_time/hash/content-drift; invalid input errors;"
      " announced in x402, agent.json, agent-tools.json, openapi.json, agents.txt and ard.json")

# ── L40: A2A agent card ────────────────────────────────────────────────────
fails40 = []
st, _, body = get("/.well-known/agent-card.json")
if st != 200:
    fails40.append(f"L40: /.well-known/agent-card.json answered {st}")
else:
    try:
        c = json.loads(body)
    except Exception as e:
        fails40.append(f"L40: agent card is not JSON: {e}")
        c = {}
    for key in ("protocolVersion", "name", "description", "url", "version", "skills"):
        if not c.get(key):
            fails40.append(f"L40: agent card is missing {key!r}")
    if not str(c.get("protocolVersion", "")).startswith("0.3"):
        fails40.append(f"L40: protocolVersion is {c.get('protocolVersion')!r}, expected a 0.3.x A2A version")
    skills = c.get("skills") or []
    ids = {s.get("id") for s in skills if isinstance(s, dict)}
    expected = {"extract_url", "check_link", "domain_info", "web_search",
                "geoip_lookup", "nano_account_info"}
    if not expected.issubset(ids):
        fails40.append(f"L40: skills missing {sorted(expected - ids)}, got {sorted(ids)}")
    for s in skills:
        if not isinstance(s, dict) or not s.get("name") or not s.get("description"):
            fails40.append(f"L40: skill {s.get('id')!r} lacks name/description")
    scheme = (c.get("securitySchemes") or {}).get("x402-nano") or {}
    if scheme.get("network") != "nano:mainnet":
        fails40.append(f"L40: security scheme network is {scheme.get('network')!r}, expected nano:mainnet")
    if not str(scheme.get("payTo", "")).startswith("nano_"):
        fails40.append(f"L40: security scheme payTo is {scheme.get('payTo')!r}, expected a nano_ account")
    prices = scheme.get("prices") or {}
    if prices.get("extract_url") != 0.0001 or prices.get("domain_info") != 0.0005:
        fails40.append(f"L40: advertised prices do not match the endpoints: {prices}")
    if c.get("security") != [{"x402-nano": []}]:
        fails40.append(f"L40: security requirement is {c.get('security')!r}, expected the x402-nano scheme")

if fails40:
    print("L40_AGENTCARD_FAIL:")
    for f in fails40:
        print("  -", f)
    sys.exit(1)
print("L40_AGENTCARD_PASS: /.well-known/agent-card.json is a conformant A2A card with 6 complete"
      " skills, the nano:mainnet x402 scheme, the treasury payTo and prices that match the endpoints")
print("STATUS_ORACLE_PASS")
PY
