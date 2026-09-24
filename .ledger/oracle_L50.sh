#!/usr/bin/env bash
# Oracle for L50: vend-client sends X-BALANCE header and supports balance/top-up.
# Runs the deterministic unit tests (no network, no real funds) and prints L50_ORACLE_PASS
# only when the full X-BALANCE client behavior holds.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=$(.venv/bin/python -m pytest test_vend_client_balance.py -q 2>&1)

# The suite must run 11 tests, all passing.
if ! printf '%s' "$OUT" | grep -q "11 passed"; then
    echo "L50 FAILED: vend-client balance tests did not all pass"
    printf '%s\n' "$OUT" | tail -20
    exit 1
fi

echo "L50_ORACLE_PASS"
