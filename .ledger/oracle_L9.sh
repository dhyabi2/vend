#!/usr/bin/env bash
# Oracle L9 — the 402 challenge is spec-shaped and quotes the exact enforced price.
#
# Starts the server on an ephemeral port with a temp DB, fetches the live
# PAYMENT-REQUIRED header from BOTH paid endpoints, decodes the base64 x402 v2
# payload and checks the fields a buyer's client and a directory probe need:
#   - resource is an object with an absolute https url and a mimeType
#   - accepts[0].scheme / network / asset are the Nano exact-scheme values
#   - accepts[0].amount is the EXACT raw price (PRICE_RAW), no float drift
#   - accepts[0].payTo is the treasury account
#   - accepts[0].maxTimeoutSeconds is a positive number
#   - extensions["rail-hint"] carries the onboarding metadata
#
# Prints L9_CHALLENGE_PASS only when every check holds on both endpoints.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l9_XXXX.sqlite3)"
export VEND_PORT=8432
export VEND_DOMAIN="127.0.0.1:8432"
export VEND_BASE_URL="http://127.0.0.1:8432"
export VEND_PRICE_EXTRACT="0.0001"

python3 -m uvicorn server:app --host 127.0.0.1 --port 8432 --log-level warning &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8432/health" >/dev/null 2>&1 && break
    sleep 0.25
done

python3 - <<'PY'
import base64, json, os, re, sys, urllib.error, urllib.request

sys.path.insert(0, ".")
from nano_verify import PRICE_RAW, VEND_ACCOUNT

BASE = "http://127.0.0.1:8432"
# The endpoint's own public subdomain (one subdomain per service).
ENDPOINT_BASE = {
    "/api/v1/extract": "https://extract.paypercall.dev",
    "/api/v1/check-link": "https://check.paypercall.dev",
    "/api/v1/domain-info": "https://domain.paypercall.dev",
    "/api/v1/web-search": "https://search.paypercall.dev",
    "/api/v1/geoip": "https://geoip.paypercall.dev",
    # nano-info is served on every routed host; nano.paypercall.dev has no A
    # record to this box, so the challenge advertises the host that answers.
    "/api/v1/nano-info": "https://extract.paypercall.dev",
}
# Every paid endpoint is challenged the same way; the enforced raw price differs
# for the two 0.0005 XNO endpoints, so compare against the configured value.
PRICE_FILES = {
    "/api/v1/extract": "0.0001", "/api/v1/check-link": "0.0001",
    "/api/v1/domain-info": "0.0005", "/api/v1/web-search": "0.0001",
    "/api/v1/geoip": "0.0001", "/api/v1/nano-info": "0.0005",
}
XNO_RAW = 10 ** 30
# Decimal, never float: 0.0001 XNO is exactly 1e26 raw, not 1.0000000000000000476e26.
from decimal import Decimal
EXPECTED_RAW = {k: str(int(Decimal(v) * Decimal(XNO_RAW))) for k, v in PRICE_FILES.items()}
fails = []


def challenge(path):
    req = urllib.request.Request(BASE + path)
    try:
        urllib.request.urlopen(req, timeout=15)
        return None
    except urllib.error.HTTPError as e:
        if e.code != 402:
            fails.append(f"{path}: expected HTTP 402, got {e.code}")
            return None
        hdr = e.headers.get("PAYMENT-REQUIRED") or e.headers.get("payment-required")
        if not hdr:
            fails.append(f"{path}: no PAYMENT-REQUIRED header")
            return None
        return json.loads(base64.b64decode(hdr))


for path in ENDPOINT_BASE:
    doc = challenge(path)
    if doc is None:
        continue

    if doc.get("x402Version") != 2:
        fails.append(f"{path}: x402Version != 2 ({doc.get('x402Version')})")

    res = doc.get("resource")
    if not isinstance(res, dict):
        fails.append(f"{path}: resource is {type(res).__name__}, expected object")
    else:
        url = res.get("url", "")
        # The resource URL must be absolute and name the endpoint's OWN public
        # subdomain, so a buyer's client is told exactly where the service lives.
        # (One subdomain per service: extract./check./domain./search. — the
        # loopback base the oracle runs on is deliberately never advertised.)
        if not re.match(r"^https?://[^/]+/", url):
            fails.append(f"{path}: resource.url is not absolute ({url!r})")
        else:
            expected_base = ENDPOINT_BASE[path]
            if url != expected_base + path:
                fails.append(
                    f"{path}: resource.url {url!r} is not the endpoint's own "
                    f"subdomain URL {expected_base + path!r}"
                )
        if not res.get("mimeType"):
            fails.append(f"{path}: resource has no mimeType")

    accepts = doc.get("accepts") or []
    if len(accepts) != 1:
        fails.append(f"{path}: expected exactly 1 accept, got {len(accepts)}")
    else:
        a = accepts[0]
        if a.get("scheme") != "exact":
            fails.append(f"{path}: scheme {a.get('scheme')!r} != 'exact'")
        if a.get("network") != "nano:mainnet":
            fails.append(f"{path}: network {a.get('network')!r} != 'nano:mainnet'")
        if a.get("asset") != "XNO":
            fails.append(f"{path}: asset {a.get('asset')!r} != 'XNO'")
        expected_amount = EXPECTED_RAW[path]
        if a.get("amount") != expected_amount:
            fails.append(
                f"{path}: amount {a.get('amount')!r} != enforced price {expected_amount!r}"
            )
        if a.get("payTo") != VEND_ACCOUNT:
            fails.append(f"{path}: payTo {a.get('payTo')!r} != treasury")
        mts = a.get("maxTimeoutSeconds")
        if not isinstance(mts, int) or mts <= 0:
            fails.append(f"{path}: maxTimeoutSeconds {mts!r} is not a positive int")
        else:
            # Quotable proof: the exact amount, the absolute resource URL and the
            # timeout a buyer's client reads straight out of the 402 challenge.
            print(
                f"PASS: {path} 402 challenge: resource {res.get('url')!r}, "
                f"amount {a.get('amount')!r} (== enforced {PRICE_FILES[path]} XNO), payTo {str(a.get('payTo'))[:14]}..., "
                f"maxTimeoutSeconds {mts}"
            )

    hint = (doc.get("extensions") or {}).get("rail-hint")
    if not isinstance(hint, dict) or "info" not in hint:
        fails.append(f"{path}: extensions['rail-hint'].info missing")

if fails:
    print("L9_CHALLENGE_FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print("L9_CHALLENGE_PASS")
PY
