#!/usr/bin/env bash
# Oracle L13 — every paid endpoint's 402 challenge names its OWN subdomain.
#
# The defect this guards against: server.py built resource.url from the single
# generic BASE_URL, so all four endpoints advertised extract.paypercall.dev,
# even on check./domain./search.  A buyer's client was told to pay at a resource
# URL belonging to a different service.  CDP's x402 validator showed it live:
#     resource "https://search.paypercall.dev/api/v1/web-search" -> challenge
#     carried "https://extract.paypercall.dev/api/v1/web-search".
#
# Starts the server on an ephemeral port with a temp DB and checks, for each
# paid endpoint, that resource.url in BOTH the PAYMENT-REQUIRED header and the
# response body is that endpoint's own subdomain URL.
#
# Prints L13_SUBDOMAIN_PASS only when all four hold.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l13_XXXX.sqlite3)"
export VEND_PORT=8452

python3 -m uvicorn server:app --host 127.0.0.1 --port 8452 --log-level warning &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8452/health" >/dev/null 2>&1 && break
    sleep 0.25
done

python3 - <<'PY'
import base64, json, sys, urllib.error, urllib.request

BASE = "http://127.0.0.1:8452"
# path -> the endpoint's own advertised subdomain base
EXPECTED = {
    "/api/v1/extract": "https://extract.paypercall.dev",
    "/api/v1/check-link": "https://check.paypercall.dev",
    "/api/v1/domain-info": "https://domain.paypercall.dev",
    "/api/v1/web-search": "https://search.paypercall.dev",
}
fails = []


def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


for path, base in EXPECTED.items():
    status, headers, body = get(path)
    if status != 402:
        fails.append(f"{path}: HTTP {status}, expected 402")
        continue

    want = base + path

    # Header challenge
    hdr = headers.get("PAYMENT-REQUIRED") or headers.get("payment-required")
    if not hdr:
        fails.append(f"{path}: no PAYMENT-REQUIRED header")
    else:
        hdr_url = json.loads(base64.b64decode(hdr)).get("resource", {}).get("url")
        if hdr_url != want:
            fails.append(f"{path}: header resource.url {hdr_url!r} != {want!r}")

    # Body challenge
    body_url = json.loads(body).get("resource", {}).get("url")
    if body_url != want:
        fails.append(f"{path}: body resource.url {body_url!r} != {want!r}")

if fails:
    print("L13_SUBDOMAIN_FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print("subdomain_challenges:", len(EXPECTED), "all correct")
print("L13_SUBDOMAIN_PASS")
PY
