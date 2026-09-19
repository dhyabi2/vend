#!/usr/bin/env bash
# Oracle L11 — Domain-info endpoint returns 402 without payment.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l11_XXXX.sqlite3)"
export VEND_PORT=8432
export VEND_DOMAIN="127.0.0.1:8432"
export VEND_BASE_URL="http://127.0.0.1:8432"
export VEND_PRICE_EXTRACT="0.0001"

SRV=""
cleanup() {
    if [ -n "$SRV" ]; then
        kill "$SRV" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start server
python3 -m uvicorn server:app --host 127.0.0.1 --port 8432 --log-level warning &
SRV=$!

# Wait for readiness
for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8432/health" >/dev/null 2>&1 && break
    sleep 0.25
done

# Test 1: Unpaid request returns 402
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8432/api/v1/domain-info")
if [ "$STATUS" != "402" ]; then
    echo "FAIL: unpaid request returned $STATUS (expected 402)"
    exit 1
fi

# Test 2: 402 response has PAYMENT-REQUIRED header
HEADER=$(curl -s -i "http://127.0.0.1:8432/api/v1/domain-info" | grep -i "payment-required" | head -1)
if [ -z "$HEADER" ]; then
    echo "FAIL: no PAYMENT-REQUIRED header"
    exit 1
fi

# Test 3: 402 body has correct endpoint and price
BODY=$(curl -s "http://127.0.0.1:8432/api/v1/domain-info")
ENDPOINT=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('endpoint',''))")
PRICE=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('price_xno',''))")
if [ "$ENDPOINT" != "/api/v1/domain-info" ]; then
    echo "FAIL: wrong endpoint in 402 body: $ENDPOINT"
    exit 1
fi
if [ "$PRICE" != "0.0005" ]; then
    echo "FAIL: wrong price in 402 body: $PRICE (expected 0.0005)"
    exit 1
fi

# Test 4: x402 manifest includes domain-info with its own price
MANIFEST=$(curl -s "http://127.0.0.1:8432/.well-known/x402")
COUNT=$(echo "$MANIFEST" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('resources',[])))")
if [ "$COUNT" != "4" ]; then
    echo "FAIL: x402 manifest has $COUNT resources (expected 4)"
    exit 1
fi

# Test 5: domain-info resource in manifest uses its own raw price
EXPECTED_RAW=$(python3 -c "from nano_verify import _price_to_raw; print(str(_price_to_raw(0.0005)))")
MANIFEST_AMOUNT=$(echo "$MANIFEST" | python3 -c "import json,sys; d=json.load(sys.stdin); r=[x for x in d['resources'] if 'domain-info' in x['url']]; print(r[0]['accepts'][0]['amount'] if r else 'missing')")
if [ "$MANIFEST_AMOUNT" != "$EXPECTED_RAW" ]; then
    echo "FAIL: domain-info resource amount $MANIFEST_AMOUNT != expected $EXPECTED_RAW"
    exit 1
fi

# Test 6: OpenAPI spec includes domain-info
OAPI=$(curl -s "http://127.0.0.1:8432/openapi.json")
HAS_DOMAIN_INFO=$(echo "$OAPI" | python3 -c "import json,sys; d=json.load(sys.stdin); print('/api/v1/domain-info' in d.get('paths',{}))")
if [ "$HAS_DOMAIN_INFO" != "True" ]; then
    echo "FAIL: domain-info not in OpenAPI spec"
    exit 1
fi

# Test 7: agent-tools manifest includes domain-info
AT=$(curl -s "http://127.0.0.1:8432/.well-known/agent-tools.json")
AT_COUNT=$(echo "$AT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('x402',{}).get('resources',[])))")
if [ "$AT_COUNT" != "4" ]; then
    echo "FAIL: agent-tools manifest has $AT_COUNT resources (expected 4)"
    exit 1
fi

echo "L11_DOMAININFO_PASS"
exit 0