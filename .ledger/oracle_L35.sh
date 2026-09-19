#!/usr/bin/env bash
# Oracle for L35 + L36: Free trial returns real data, 5/IP/day, 402 when exhausted
# Tests via direct connection (127.0.0.1:8402) to control X-Forwarded-For.
#
# L35: any IP gets 5 real-data calls per day across all endpoints without paying,
#      tracked in-memory with an IP-keyed counter that resets daily.
# L36: trial returns real module data, not fake/demo data — the same
#      extract/check/domain/search/geoip/nano-info function that a paid call uses,
#      but with free_trial=True and trial_remaining N.
#
# The oracle restarts the vend server so the in-memory tracker starts fresh.

set -uo pipefail
BASE="${VEND_BASE:-http://127.0.0.1:8402}"

echo "--- Restarting vend server for clean trial state ---"
systemctl restart vend-api 2>&1
# Wait for server to be ready
for i in $(seq 1 12); do
    if curl -s -o /dev/null -w "" "$BASE/health" 2>/dev/null; then
        break
    fi
    sleep 1
done
echo "Server ready"

# Unique IP for this run
IP="trialtest-$$-$(date +%s)"

fail=""
pass()  { echo "  PASS: $1"; }
fail_f() { echo "  FAIL: $1"; fail=1; }

# ── L35.1: Bare probe must still return 402 ──
echo ""
echo "=== L35.1: Bare probe returns 402 ==="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/extract" -H "X-Forwarded-For: $IP")
if [[ "$code" == "402" ]]; then
    pass "Bare probe (no input) returns 402 for x402 conformance"
else
    fail_f "Bare probe expected 402 got $code"
fi

# ── L35.2 + L36: First real call → 200 with trial headers and real module data ──
echo ""
echo "=== L35.2 + L36: Trial returns 200 with real data ==="
headers=$(curl -s -D - -o /tmp/l35_trial1.json \
    "$BASE/api/v1/extract?url=https://example.com" -H "X-Forwarded-For: $IP")
code=$(echo "$headers" | head -1 | awk '{print $2}')
if [[ "$code" == "200" ]]; then
    pass "GET /api/v1/extract?url=... returns 200"
else
    fail_f "Expected 200 got $code"
fi

hdr_rem=$(echo "$headers" | grep -i x-trial-remaining: | sed 's/.*: *//;s/\r//')
hdr_lim=$(echo "$headers" | grep -i x-trial-limit: | sed 's/.*: *//;s/\r//')
if [[ "$hdr_rem" == "4" ]]; then
    pass "x-trial-remaining=4"
else
    fail_f "expected x-trial-remaining=4 got $hdr_rem"
fi
if [[ "$hdr_lim" == "5" ]]; then
    pass "x-trial-limit=5"
else
    fail_f "expected x-trial-limit=5 got $hdr_lim"
fi

# Verify real module data (L36)
body=$(cat /tmp/l35_trial1.json)
title=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('title',''))")
text_len=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('text','')))")
pay_free=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); p=d.get('payment',{}); print(p.get('free_trial')==True)")
pay_rem=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); p=d.get('payment',{}); print(p.get('trial_remaining'))")
pay_xno=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('payment',{}).get('amount_xno',''))")

if [[ "$title" == "Example Domain" ]]; then
    pass "Real title from trafilatura: $title"
else
    fail_f "Expected 'Example Domain' got '$title'"
fi
if [[ "$text_len" -gt 10 ]]; then
    pass "Real content: $text_len chars"
else
    fail_f "Expected text > 10 chars got $text_len"
fi
if [[ "$pay_free" == "True" ]]; then
    pass "payment.free_trial=True"
else
    fail_f "Expected free_trial=True"
fi
if [[ "$pay_rem" == "4" ]]; then
    pass "payment.trial_remaining=4"
else
    fail_f "Expected trial_remaining=4 got $pay_rem"
fi
if [[ "$pay_xno" == "0.000000" ]]; then
    pass "payment.amount_xno=0 (free)"
else
    fail_f "Expected amount_xno=0 got $pay_xno"
fi

# ── L35.3: Exhaustion — 5 total, 6th → 402 ──
echo ""
echo "=== L35.3: Exhaustion after 5 calls ==="
# Already made 1 real call. Make 4 more to reach limit.
for i in $(seq 1 4); do
    curl -s -o /dev/null "$BASE/api/v1/extract?url=https://example.com&_=$i" -H "X-Forwarded-For: $IP"
done
code6=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/extract?url=https://example.com&_=x" -H "X-Forwarded-For: $IP")
if [[ "$code6" == "402" ]]; then
    pass "6th call from same IP returns 402 (5/5 used)"
else
    fail_f "Expected 402 on exhausted trial got $code6"
fi

# ── L35.4: Per-IP isolation ──
echo ""
echo "=== L35.4: Per-IP isolation ==="
IP2="trialtest-B-$$-$(date +%s)"
code2=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/extract?url=https://example.com" -H "X-Forwarded-For: $IP2")
if [[ "$code2" == "200" ]]; then
    pass "Second fresh IP gets its own trial (200)"
else
    fail_f "Second IP expected 200 got $code2"
fi
hdr2=$(curl -s -D - -o /dev/null "$BASE/api/v1/extract?url=https://example.com" -H "X-Forwarded-For: $IP2" 2>&1)
rem2=$(echo "$hdr2" | grep -i x-trial-remaining: | sed 's/.*: *//;s/\r//')
if [[ "$rem2" == "3" ]]; then
    pass "Second IP's own budget: remaining=3"
else
    fail_f "Second IP expected remaining=3 got $rem2"
fi

# ── Cleanup ──
rm -f /tmp/l35_trial1.json

if [[ -n "$fail" ]]; then
    echo ""
    echo "L35_ORACLE_FAIL"
    exit 1
fi
echo ""
echo "L35_ORACLE_PASS"
exit 0