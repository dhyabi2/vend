#!/bin/bash
# Oracle for: "A bare probe of /api/v1/address-verdict (no params, no payment)
# returns HTTP 402 with the Nano x402 challenge, so x402 discovery crawlers
# find the endpoint as a paid resource (was 422 before the fix)."
set -uo pipefail
BASE="${1:-https://extract.paypercall.dev}"
code=$(curl -s -o /tmp/_verdict_body -w "%{http_code}" --max-time 20 "$BASE/api/v1/address-verdict")
if [ "$code" != "402" ]; then
    echo "ORACLE_FAIL: bare probe returned HTTP $code (need 402)"
    exit 1
fi
# Response must be the payment challenge, not a param-validation error.
if ! grep -q "payment_required" /tmp/_verdict_body; then
    echo "ORACLE_FAIL: 402 body missing 'payment_required': $(head -c 200 /tmp/_verdict_body)"
    exit 1
fi
if ! grep -q '"price_xno"' /tmp/_verdict_body; then
    echo "ORACLE_FAIL: 402 body missing price_xno"
    exit 1
fi
echo "L57_VERDICT402_PASS: bare /api/v1/address-verdict answered $code with the Nano x402 challenge"
