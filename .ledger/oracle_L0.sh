#!/usr/bin/env bash
# Oracle for L0: Server starts on port 8402, /health returns 200,
# paid endpoints return 402 without payment.
# Exits 0 only if both conditions hold.
set -euo pipefail

HOST="${VEND_TEST_HOST:-localhost}"
PORT="${VEND_TEST_PORT:-8402}"
BASE="http://${HOST}:${PORT}"

# Check /health returns 200 with status ok
health_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/health")
health_body=$(curl -s "${BASE}/health")
health_ok=$(echo "$health_body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status')=='ok' and len(d.get('payment_address',''))>0)" 2>/dev/null)

echo "health_status=${health_code} body_ok=${health_ok}"

# Check /api/v1/extract without payment returns 402
extract_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/api/v1/extract?url=https://example.com")
extract_body=$(curl -s "${BASE}/api/v1/extract?url=https://example.com")
extract_has_402_error=$(echo "$extract_body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('payment_required' in str(d))" 2>/dev/null)

echo "extract_code=${extract_code} has_402=${extract_has_402_error}"

# Verify
if [ "$health_code" = "200" ] && [ "$health_ok" = "True" ] && [ "$extract_code" = "402" ] && [ "$extract_has_402_error" = "True" ]; then
    echo "L0_ORACLE_PASS"
    exit 0
else
    echo "L0_ORACLE_FAIL"
    exit 1
fi