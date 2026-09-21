#!/usr/bin/env bash
# Oracle L56 — PAYMENT-SIGNATURE (x402 exact / feeless402) acceptance.
#
# Law: "A request carrying a PAYMENT-SIGNATURE header (a base64 PaymentPayload
# with a signed Nano send block) is accepted and settled like a self-broadcast
# payment: the block is parsed, broadcast via Nano RPC, confirmed, and its
# on-ledger hash feeds the same verify/redeem path as X-PAYMENT. Destination
# mismatches and unsigned blocks are refused without broadcasting."
#
# Scope: nano_verify.py, server.py, tests/test_payment_signature.py
# Test: the PAYMENT-SIGNATURE unit tests all pass against a stubbed Nano RPC.
set -uo pipefail
cd /root/vend
FAIL=0

out=$(python3 tests/test_payment_signature.py 2>&1) || FAIL=1
echo "$out"
if ! echo "$out" | grep -q "All PAYMENT-SIGNATURE tests PASSED"; then
    FAIL=1
fi

# Statically confirm server.py wires the new path into require_payment.
if ! grep -q "confirm_signature_payment" server.py; then
    echo "FAIL: server.py does not call confirm_signature_payment"
    FAIL=1
fi
if ! grep -q "PAYMENT-SIGNATURE" server.py; then
    echo "FAIL: server.py has no PAYMENT-SIGNATURE acceptance block"
    FAIL=1
fi

[ $FAIL -eq 0 ] && echo "L56_PASS" || echo "L56_FAIL"
exit $FAIL
