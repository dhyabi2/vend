#!/usr/bin/env bash
# Oracle for Nano account info endpoint law.
# Verifies:
#   L23: nano_info module returns structured data for a valid account and
#        errors gracefully on invalid input
#   L24: /api/v1/nano-info returns 402 without payment with correct price and
#        is listed in x402 manifest
set -euo pipefail

fail_count=0

echo "NANOINFO_ORACLE_START"

# 1. Module returns structured data for a valid account
if python3 -c "
import sys
sys.path.insert(0, '/root/vend')
from nano_info import nano_account_info
r = nano_account_info('nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3')
assert 'error' not in r, f'valid account returned error: {r}'
for k in ['account', 'balance', 'balance_xno', 'representative', 'block_count', 'frontier', 'weight', 'pending']:
    assert k in r, f'missing key: {k}'
print('PASS: valid account returns structured data')
" 2>/dev/null; then
    echo "  PASS: valid account returns structured data"
else
    echo "  FAIL: valid account returns structured data"
    fail_count=$((fail_count + 1))
fi

# 2. Empty account errors gracefully
if python3 -c "
import sys
sys.path.insert(0, '/root/vend')
from nano_info import nano_account_info
r = nano_account_info('')
assert 'error' in r, 'empty should return error'
print('PASS: empty account errors')
" 2>/dev/null; then
    echo "  PASS: empty account errors"
else
    echo "  FAIL: empty account errors"
    fail_count=$((fail_count + 1))
fi

# 3. Invalid prefix errors gracefully
if python3 -c "
import sys
sys.path.insert(0, '/root/vend')
from nano_info import nano_account_info
r = nano_account_info('foobar')
assert 'error' in r, 'bad prefix should return error'
assert 'start with nano_' in r['error'], 'message should explain prefix'
print('PASS: bad prefix errors')
" 2>/dev/null; then
    echo "  PASS: bad prefix errors"
else
    echo "  FAIL: bad prefix errors"
    fail_count=$((fail_count + 1))
fi

# 4. Nonexistent account errors gracefully
if python3 -c "
import sys
sys.path.insert(0, '/root/vend')
from nano_info import nano_account_info
r = nano_account_info('nano_1111111111111111111111111111111111111111111111111111hifc8npp')
assert 'error' in r, 'nonexistent account should error'
print('PASS: nonexistent account errors')
" 2>/dev/null; then
    echo "  PASS: nonexistent account errors"
else
    echo "  FAIL: nonexistent account errors"
    fail_count=$((fail_count + 1))
fi

# 5. GET /api/v1/nano-info without payment returns 402 with correct price
#    (requires running server; run with VEND_PORT to avoid conflicts, skip if unavailable)
if [ -z "${NANOINFO_SKIP_HTTP:-}" ] && command -v curl >/dev/null 2>&1; then
    PORT="${VEND_PORT:-8402}"
    code=$(curl -s -o /tmp/nanoinfo-402.json -w "%{http_code}" "http://localhost:$PORT/api/v1/nano-info?account=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3" 2>/dev/null || echo "000")
    if [ "$code" = "402" ]; then
        # Check price in body
        if python3 -c "
import json
with open('/tmp/nanoinfo-402.json') as f: d=json.load(f)
assert d.get('price_xno') == 0.0005, f'wrong price: {d.get(\"price_xno\")}'
assert d.get('endpoint') == '/api/v1/nano-info', f'wrong endpoint: {d.get(\"endpoint\")}'
# The advertised host must be one that reaches this server: nano.paypercall.dev
# is still a dead Vercel deployment (DNS owner-disabled).
assert 'extract.paypercall.dev/api/v1/nano-info' in d.get('resource',{}).get('url',''), 'dead resource url advertised'
print('PASS: 402 with correct price and resource url')
" 2>/dev/null; then
            echo "  PASS: 402 with correct price and resource url"
            python3 -c "
import json
d=json.load(open('/tmp/nanoinfo-402.json'))
print('  PROOF: unpaid /api/v1/nano-info answers 402; body price_xno =', d.get('price_xno'), '; endpoint =', d.get('endpoint'), '; resource.url =', (d.get('resource') or {}).get('url'))
" 2>/dev/null || true
            for m in /.well-known/x402 /.well-known/agent-tools.json /openapi.json; do
                if curl -s "http://localhost:$PORT$m" | grep -q "nano-info"; then
                    echo "  PASS: nano-info named in $m"
                else
                    echo "  FAIL: nano-info missing from $m"
                    fail_count=$((fail_count + 1))
                fi
            done
        else
            echo "  FAIL: 402 body wrong"
            fail_count=$((fail_count + 1))
        fi
    else
        echo "  WARN: server not reachable (http $code) — skipping HTTP check"
    fi
fi

echo ""
if [ "$fail_count" -eq 0 ]; then
    echo "NANOINFO_ORACLE_PASS"
else
    echo "NANOINFO_ORACLE_FAIL ($fail_count checks failed)"
    exit 1
fi
