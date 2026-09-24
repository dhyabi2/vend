#!/usr/bin/env bash
# Oracle L14 — the 402 body carries a payable x402 challenge.
#
# The defect this guards against: the challenge existed only in the
# PAYMENT-REQUIRED header.  An independent conformance checker (StelarDigital
# x402-doctor) flagged it live:
#     challenge_in_body: warn — "The 402 challenge is only in the
#     Payment-Required response header, not the response body — body-reading
#     clients will fail closed. The x402 spec expects the challenge in both
#     places."
# and separately:
#     input_schema: warn — "extensions.bazaar.info.input is missing — required
#     by x402scan and agent tooling to know what to send. Buyers may fail closed
#     rather than guess."
#
# For every paid endpoint this checks the BODY is JSON carrying:
#   - x402Version 2
#   - resource.url == the endpoint's own subdomain URL
#   - accepts[0] with scheme/network/asset/amount/payTo/maxTimeoutSeconds
#   - extensions.bazaar.info.input.schema and .example (the request shape)
# and that the body's accepts[0] matches the header's accepts[0] exactly, so
# the two transports cannot disagree about the price.
#
# Prints L14_BODYCHALLENGE_PASS only when all four endpoints hold.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l14_XXXX.sqlite3)"
export VEND_PORT=8462
export VEND_PRICE_EXTRACT="0.0001"

python3 -m uvicorn server:app --host 127.0.0.1 --port 8462 --log-level warning &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8462/health" >/dev/null 2>&1 && break
    sleep 0.25
done

python3 - <<'PY'
import base64, json, sys, urllib.error, urllib.request

BASE = "http://127.0.0.1:8462"
PAID = {
    "/api/v1/extract": "https://extract.paypercall.dev",
    "/api/v1/check-link": "https://check.paypercall.dev",
    "/api/v1/domain-info": "https://domain.paypercall.dev",
    "/api/v1/web-search": "https://search.paypercall.dev",
}
REQUIRED_ACCEPT = ("scheme", "network", "asset", "amount", "payTo", "maxTimeoutSeconds")
fails = []


def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


for path, base in PAID.items():
    status, headers, body = get(path)
    if status != 402:
        fails.append(f"{path}: HTTP {status}, expected 402")
        continue

    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        fails.append(f"{path}: 402 body is not JSON (body-reading client fails closed)")
        continue

    if doc.get("x402Version") != 2:
        fails.append(f"{path}: body x402Version {doc.get('x402Version')!r} != 2")

    want = base + path
    if doc.get("resource", {}).get("url") != want:
        fails.append(f"{path}: body resource.url {doc.get('resource', {}).get('url')!r} != {want!r}")

    accepts = doc.get("accepts") or []
    if len(accepts) != 1:
        fails.append(f"{path}: body has {len(accepts)} accepts, expected 1")
    else:
        missing = [k for k in REQUIRED_ACCEPT if k not in accepts[0]]
        if missing:
            fails.append(f"{path}: body accepts[0] missing {missing}")
        elif accepts[0].get("network") != "nano:mainnet" or accepts[0].get("asset") != "XNO":
            fails.append(f"{path}: body accepts[0] is not the Nano rail")

    # The request shape a buyer needs BEFORE paying.
    bazaar = (doc.get("extensions") or {}).get("bazaar") or {}
    info = bazaar.get("info") or {}
    schema = (info.get("input") or {}).get("schema") or {}
    if not schema.get("properties"):
        fails.append(f"{path}: extensions.bazaar.info.input.schema is missing (buyer must guess)")
    if not (info.get("input") or {}).get("example"):
        fails.append(f"{path}: extensions.bazaar.info.input.example is missing")

    # Body and header must agree on the price — two transports, one truth.
    hdr = headers.get("PAYMENT-REQUIRED") or headers.get("payment-required")
    if not hdr:
        fails.append(f"{path}: no PAYMENT-REQUIRED header")
    else:
        hdr_accepts = json.loads(base64.b64decode(hdr)).get("accepts")
        if hdr_accepts != accepts:
            fails.append(f"{path}: body accepts {accepts!r} != header accepts {hdr_accepts!r}")

if fails:
    print("L14_BODYCHALLENGE_FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print("body_challenges:", len(PAID), "all payable, schema published")
print("L14_BODYCHALLENGE_PASS")
PY
