#!/usr/bin/env bash
# Oracle L32: Payment recovery retries a failed paid call exactly once.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== L32: Payment recovery test ==="

# Run the recovery-specific tests
.venv/bin/pytest test_paid_response.py::test_run_paid_work_recovery_success \
    test_paid_response.py::test_run_paid_work_recovery_double_failure \
    test_paid_response.py::test_run_paid_work_recovery_resets_failure_counter_on_success \
    -v 2>&1

echo ""
echo "L32_ORACLE_PASS"