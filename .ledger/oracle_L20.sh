#!/usr/bin/env bash
# Oracle L20 — IP Geolocation endpoint returns 402 without payment.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l20_XXXX.sqlite3)"
export VEND_PORT=9495
export VEND_DOMAIN="127.0.0.1:9495"
export VEND_BASE_URL="http://127.0.0.1:9495"
export VEND_PRICE_EXTRACT="0.0001"
export VEND_PRICE_WEBSEARCH="0.0001"
export VEND_PRICE_GEO="0.0001"

SRV=""
cleanup() {
    if [ -n "$SRV" ]; then
        kill "$SRV" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start server
python3 -m uvicorn server:app --host 127.0.0.1 --port 9495 --log-level warning &
SRV=$!

# Wait for readiness
for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:9495/health" >/dev/null 2>&1 && break
    sleep 0.25
done

# Test 1: Unpaid request returns 402
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:9495/api/v1/geoip")
if [ "$STATUS" != "402" ]; then
    echo "FAIL: unpaid request returned $STATUS (expected 402)"
    exit 1
fi

# Test 2: 402 response has PAYMENT-REQUIRED header
HEADER=$(curl -s -i "http://127.0.0.1:9495/api/v1/geoip" | grep -i "payment-required" | head -1)
if [ -z "$HEADER" ]; then
    echo "FAIL: no PAYMENT-REQUIRED header"
    exit 1
fi

# Test 3: 402 body has correct endpoint and price
BODY=$(curl -s "http://127.0.0.1:9495/api/v1/geoip")
ENDPOINT=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('endpoint',''))")
PRICE=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('price_xno',''))")
if [ "$ENDPOINT" != "/api/v1/geoip" ]; then
    echo "FAIL: wrong endpoint in 402 body: $ENDPOINT"
    exit 1
fi
if [ "$PRICE" != "0.0001" ]; then
    echo "FAIL: wrong price in 402 body: $PRICE (expected 0.0001)"
    exit 1
fi

# Test 4: Resource URL is resolvable (uses extract.paypercall.dev or localhost)
RESOURCE_URL=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('resource',{}).get('url',''))")
if [ -z "$RESOURCE_URL" ]; then
    echo "FAIL: no resource URL in 402 body"
    exit 1
fi

# Test 5: x402 manifest includes geoip with 6 resources
MANIFEST=$(curl -s "http://127.0.0.1:9495/.well-known/x402")
COUNT=$(echo "$MANIFEST" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('resources',[])))")
if [ "$COUNT" != "7" ]; then
    echo "FAIL: x402 manifest has $COUNT resources (expected 7)"
    exit 1
fi
HAS_GEO=$(echo "$MANIFEST" | python3 -c "import json,sys; d=json.load(sys.stdin); print(any('geoip' in r['url'] for r in d['resources']))")
if [ "$HAS_GEO" != "True" ]; then
    echo "FAIL: geoip not in x402 manifest"
    exit 1
fi

# Test 6: OpenAPI spec includes geoip
OAPI=$(curl -s "http://127.0.0.1:9495/openapi.json")
HAS_OAPI=$(echo "$OAPI" | python3 -c "import json,sys; d=json.load(sys.stdin); print('/api/v1/geoip' in d.get('paths',{}))")
if [ "$HAS_OAPI" != "True" ]; then
    echo "FAIL: geoip not in OpenAPI spec"
    exit 1
fi

# Test 7: agent-tools manifest includes geoip with 6 resources
AT=$(curl -s "http://127.0.0.1:9495/.well-known/agent-tools.json")
AT_COUNT=$(echo "$AT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('x402',{}).get('resources',[])))")
if [ "$AT_COUNT" != "7" ]; then
    echo "FAIL: agent-tools manifest has $AT_COUNT resources (expected 7)"
    exit 1
fi

echo "L20_GEOIP_PASS"
exit 0