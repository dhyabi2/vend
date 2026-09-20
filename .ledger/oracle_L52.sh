#!/usr/bin/env bash
# Oracle L52 — Live server balance endpoints and access control.
#
# Law: "Live server serves balance endpoints with correct error handling
# and access control."
# Scope: server.py
# Test:
#   1. GET /api/v1/balance (no params) → 400 + account_required
#   2. GET /api/v1/balance with valid account → 200 + balance_raw
#   3. GET /api/v1/balance with invalid account → still 200 (lenient)
#   4. GET /api/v1/balance/topups (no params) → 400 + account_required
#   5. GET /api/v1/admin/balances → 403 from external
#   6. X-BALANCE with unknown account on a paid endpoint → 402 (not 500)
set -uo pipefail
cd /root/vend
FAIL=0
BASE="https://extract.paypercall.dev"

check() {
    local desc="$1" url="$2" expect_code="$3" expect_body="$4"
    local out code
    out=$(curl -s --max-time 15 -o /tmp/vend_L52_body.txt -w "%{http_code}" "$url" 2>&1)
    code=$?
    if [ "$code" != "0" ]; then
        echo "FAIL: $desc — curl error $code"
        return 1
    fi
    local http_code
    http_code=$(cat /tmp/vend_L52_body.txt 2>/dev/null || echo "000")
    [ "$http_code" = "" ] && http_code="000"
    # shellcheck disable=SC2155
    local body=$(cat /tmp/vend_L52_body.txt 2>/dev/null || echo "NO_BODY")
    
    [ "$http_code" = "$(echo "$http_code" | head -1)" ] 2>/dev/null
    
    # The actual http_code is in /tmp/vend_L52_http.txt
}

# We'll do this inline instead
echo "Probing live server at $BASE..."

FAIL=0

# Test 1: GET /api/v1/balance (no params) → 400 + account_required
echo -n "Test 1: balance without params -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t1.json -w "%{http_code}" "$BASE/api/v1/balance" 2>&1)
if [ "$code" != "400" ]; then
    echo "FAIL: expected HTTP 400, got $code"
    FAIL=1
else
    body=$(cat /tmp/vend_L52_t1.json)
    if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('error') == 'account_required', f'wrong error: {d}'; assert 'account' in d.get('message','')" 2>/dev/null; then
        echo "PASS"
    else
        echo "FAIL: wrong body: $(echo "$body" | head -c 100)"
        FAIL=1
    fi
fi

# Test 2: GET /api/v1/balance with valid account → 200 + balance_raw
echo -n "Test 2: balance with valid account -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t2.json -w "%{http_code}" "$BASE/api/v1/balance?account=nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7" 2>&1)
if [ "$code" != "200" ]; then
    echo "FAIL: expected HTTP 200, got $code"
    FAIL=1
else
    body=$(cat /tmp/vend_L52_t2.json)
    if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'balance_raw' in d; assert 'balance_xno' in d; assert 'account' in d" 2>/dev/null; then
        echo "PASS"
    else
        echo "FAIL: missing expected fields: $(echo "$body" | head -c 100)"
        FAIL=1
    fi
fi

# Test 3: GET /api/v1/balance with invalid string → still 200 (lenient API)
echo -n "Test 3: balance with non-nano string -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t3.json -w "%{http_code}" "$BASE/api/v1/balance?account=not_a_nano_address" 2>&1)
if [ "$code" != "200" ]; then
    echo "FAIL: expected HTTP 200, got $code"
    FAIL=1
else
    echo "PASS (lenient — accepts any string)"
fi

# Test 4: GET /api/v1/balance/topups without account → 400 + account_required
echo -n "Test 4: balance/topups without account -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t4.json -w "%{http_code}" "$BASE/api/v1/balance/topups" 2>&1)
if [ "$code" != "400" ]; then
    echo "FAIL: expected HTTP 400, got $code"
    FAIL=1
else
    body=$(cat /tmp/vend_L52_t4.json)
    if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('error') == 'account_required'" 2>/dev/null; then
        echo "PASS"
    else
        echo "FAIL: wrong body: $(echo "$body" | head -c 100)"
        FAIL=1
    fi
fi

# Test 5: GET /api/v1/admin/balances → 403 from external
echo -n "Test 5: admin/balances from external -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t5.json -w "%{http_code}" "$BASE/api/v1/admin/balances" 2>&1)
if [ "$code" != "403" ]; then
    echo "FAIL: expected HTTP 403, got $code"
    FAIL=1
else
    body=$(cat /tmp/vend_L52_t5.json)
    if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('error') == 'local_only'" 2>/dev/null; then
        echo "PASS"
    else
        echo "FAIL: wrong body: $(echo "$body" | head -c 100)"
        FAIL=1
    fi
fi

# Test 6: X-BALANCE with unknown account on a paid endpoint → 402 (not 500)
echo -n "Test 6: X-BALANCE unknown account -> "
code=$(curl -s --max-time 15 -o /tmp/vend_L52_t6.json -w "%{http_code}" \
    -H "X-BALANCE: nano_uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu99" \
    "$BASE/api/v1/status?url=https://example.com" 2>&1)
if [ "$code" != "402" ]; then
    echo "FAIL: expected HTTP 402, got $code (could be 200 free trial)"
    FAIL=1
else
    echo "PASS (correctly returns 402)"
fi

# Report
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "L52_PASS"
else
    echo "L52_FAIL"
fi
exit "$FAIL"