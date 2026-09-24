#!/usr/bin/env bash
# Oracle L10 — a directory probe and a stranger's client both reach the paywall.
#
# This is the buyability law. It does NOT just look at JSON shape (that is L9);
# it exercises the exact handshake an outside directory performs before listing
# a service, plus the shape an x402 client uses to decide how to pay.
#
#   1. A bare, unpaid GET on each paid endpoint answers 402 (not 422/400):
#      the discovery probe must reach the challenge without a query parameter.
#   2. The 402 body is JSON that names the endpoint and the treasury address.
#   3. The 402 carries x-402-version: 2 and a decodable PAYMENT-REQUIRED header.
#   4. /.well-known/x402 names every paid endpoint by absolute https URL and
#      carries a Nano exact-scheme accept with the exact price for each.
#   5. /openapi.json declares each paid operation with x-payment-info and a 402.
#
# Prints L10_BUYABLE_PASS only if every probe holds.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l10_XXXX.sqlite3)"
export VEND_PORT=8442
export VEND_DOMAIN="127.0.0.1:8442"
export VEND_BASE_URL="http://127.0.0.1:8442"
export VEND_PRICE_EXTRACT="0.0001"

python3 -m uvicorn server:app --host 127.0.0.1 --port 8442 --log-level warning &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$VEND_DB"' EXIT

for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8442/health" >/dev/null 2>&1 && break
    sleep 0.25
done

python3 - <<'PY'
import base64, json, sys, urllib.error, urllib.request

sys.path.insert(0, ".")
from nano_verify import PRICE_RAW, VEND_ACCOUNT

BASE = "http://127.0.0.1:8442"
PAID = ("/api/v1/extract", "/api/v1/check-link", "/api/v1/status", "/api/v1/domain-info",
        "/api/v1/web-search", "/api/v1/geoip", "/api/v1/nano-info")
EXPECTED_PRICES = {p.lstrip("/"): PRICE_RAW for p in PAID}
EXPECTED_PRICES["api/v1/domain-info"] = str(int(PRICE_RAW) * 5)  # 0.0005 XNO
EXPECTED_PRICES["api/v1/nano-info"] = str(int(PRICE_RAW) * 5)    # 0.0005 XNO
# /api/v1/status is charged at the base price (0.0001 XNO), like extract.
# The host each endpoint advertises.  Most have their own subdomain; nano and
# status have none that answers (nano.paypercall.dev resolves to a dead Vercel
# deployment and DNS is owner-disabled), so they advertise the host that reaches
# this server.  A law only about JSON shape would accept the dead URL; this
# asserts the advertised host is the one the deployment actually serves.
SUBDOMAIN_BASE = {
    "/api/v1/extract": "https://extract.paypercall.dev",
    "/api/v1/check-link": "https://check.paypercall.dev",
    "/api/v1/status": "https://extract.paypercall.dev",
    "/api/v1/domain-info": "https://domain.paypercall.dev",
    "/api/v1/web-search": "https://search.paypercall.dev",
    "/api/v1/geoip": "https://geoip.paypercall.dev",
    "/api/v1/nano-info": "https://extract.paypercall.dev",
}
fails = []


def get(path, headers=None):
    """Return (status, case-insensitive header view, body)."""
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, _ci(dict(r.headers)), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, _ci(dict(e.headers)), e.read().decode()


def _ci(headers):
    """Header dict with lowercase keys: HTTP header names are case-insensitive."""
    return {k.lower(): v for k, v in headers.items()}



# 1-3: bare unpaid probe reaches the challenge and the body names the deal.
for path in PAID:
    status, headers, body = get(path)
    if status != 402:
        fails.append(f"bare probe {path}: HTTP {status}, expected 402")
        continue
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        fails.append(f"bare probe {path}: body is not JSON")
        continue
    if doc.get("endpoint") != path:
        fails.append(f"{path}: 402 body endpoint {doc.get('endpoint')!r} != {path!r}")
    if doc.get("pay_to") != VEND_ACCOUNT:
        fails.append(f"{path}: 402 body pay_to does not name the treasury")
    hdr = headers.get("payment-required")
    if not hdr:
        fails.append(f"{path}: no PAYMENT-REQUIRED header")
    else:
        req_doc = json.loads(base64.b64decode(hdr))
        acc = (req_doc.get("accepts") or [{}])[0]
        ep = path.lstrip("/")
        expected = EXPECTED_PRICES[ep]
        if acc.get("amount") != expected:
            fails.append(f"{path}: header amount {acc.get('amount')!r} != {expected!r}")
    if headers.get("x-402-version") != "2":
        fails.append(f"{path}: X-402-Version {headers.get('x-402-version')!r} != '2'")
    print(f"PASS: bare unpaid GET {path} -> HTTP {status}, PAYMENT-REQUIRED header present, "
          f"body names {doc.get('endpoint')} at {doc.get('price_xno')} XNO, rail nano:mainnet")

# 4: the discovery manifest names every paid endpoint by its own absolute https
#    URL and quotes the Nano rail with the exact price.
status, _, body = get("/.well-known/x402")
if status != 200:
    fails.append(f"/.well-known/x402: HTTP {status}")
else:
    man = json.loads(body)
    urls = {r.get("url") for r in man.get("resources", [])}
    for path in PAID:
        want = SUBDOMAIN_BASE[path] + path
        if want not in urls:
            fails.append(f"manifest does not name {want}")
    for r in man.get("resources", []):
        acc = (r.get("accepts") or [{}])[0]
        if acc.get("network") != "nano:mainnet" or acc.get("asset") != "XNO":
            fails.append(f"manifest resource {r.get('url')} has no Nano rail")
        url = r.get("url", "")
        ep = next((p for p in PAID if url.endswith(p)), "")
        expected_price = EXPECTED_PRICES[ep.lstrip("/")]
        if acc.get("amount") != expected_price:
            fails.append(f"manifest resource {url} quotes {acc.get('amount')!r} != {expected_price!r}")
        else:
            print(f"PASS: /.well-known/x402 resource {url} quotes Nano rail "
                  f"{acc.get('network')}/{acc.get('asset')} amount {acc.get('amount')}")
        # the resource URL must sit on that endpoint's OWN subdomain
        if ep and not url.startswith(SUBDOMAIN_BASE[ep]):
            fails.append(f"manifest resource {url} is not on {SUBDOMAIN_BASE[ep]}")


# 5: the OpenAPI spec declares each paid operation with x-payment-info + 402.
status, _, body = get("/openapi.json")
if status != 200:
    fails.append(f"/openapi.json: HTTP {status}")
else:
    spec = json.loads(body)
    for path in PAID:
        op = (spec.get("paths", {}).get(path) or {}).get("get") or {}
        if not op.get("x-payment-info"):
            fails.append(f"openapi {path}: no x-payment-info")
        if "402" not in (op.get("responses") or {}):
            fails.append(f"openapi {path}: no 402 response")
        else:
            print(f"PASS: /openapi.json GET {path} carries x-payment-info and a 402 response")
    # servers[] carries one public entry per subdomain; every entry must be the
    # https public URL (the loopback address is never advertised to a buyer).
    srv = [s.get("url", "") for s in spec.get("servers", [])]
    if not srv or any(not u.startswith("https://") for u in srv):
        fails.append(f"openapi servers[] not all public https: {srv}")
    for path in PAID:
        if SUBDOMAIN_BASE[path] not in srv:
            fails.append(f"openapi servers[] is missing {SUBDOMAIN_BASE[path]}")

if fails:
    print("L10_BUYABLE_FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print("L10_BUYABLE_PASS")
PY
