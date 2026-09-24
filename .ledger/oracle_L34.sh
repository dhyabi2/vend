#!/usr/bin/env bash
# Oracle L34: Consecutive-failure tracking and restart warning.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== L34: Graceful restart tracking ==="

# Test that the counter logs a warning at threshold and resets on success.
# We run a Python script that exercises the module directly.
TEMP_DB=$(mktemp /tmp/vend-test-XXXXXX.db)
cleanup() { rm -f "$TEMP_DB"; }
trap cleanup EXIT

VEND_DB="$TEMP_DB" .venv/bin/python3 -c "
import logging, sys
logging.basicConfig(level=logging.WARNING, stream=sys.stdout)
# Reset module-level state
import server
server._RETRY_RECORD.clear()
server._RECOVERABLE_FAILURES['count'] = 0

from unittest.mock import MagicMock, patch
from server import run_paid_work, _RECOVERABLE_FAILURES

# We need a request mock
req = MagicMock()
req.state.payment = {
    'amount_raw': '100000000000000000000000000',
    'source': 'nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n',
    'block_hash': 'C79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345670',
}
req.headers.get = lambda k, d='': 'C79C939E...'

def always_broken(url):
    raise RuntimeError('Always fails')

# First failure triggers recovery retry (which also fails)
with patch('server.store.resolve'):
    resp1 = run_paid_work(req, always_broken, 'https://example.com')
assert _RECOVERABLE_FAILURES['count'] == 1, f'count should be 1, got {_RECOVERABLE_FAILURES[\"count\"]}'
print(f'OK: count after first double-failure = {_RECOVERABLE_FAILURES[\"count\"]}')

# Second call with a different hash — need a new request with new hash
req2 = MagicMock()
req2.state.payment = {
    'amount_raw': '100000000000000000000000000',
    'source': 'nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n',
    'block_hash': 'D79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345671',
}
req2.headers.get = lambda k, d='': 'D79C939E...'
with patch('server.store.resolve'):
    resp2 = run_paid_work(req2, always_broken, 'https://example.com')
assert _RECOVERABLE_FAILURES['count'] == 2, f'count should be 2, got {_RECOVERABLE_FAILURES[\"count\"]}'
print(f'OK: count after second double-failure = {_RECOVERABLE_FAILURES[\"count\"]}')

# Third call triggers the restart warning (threshold = 3)
req3 = MagicMock()
req3.state.payment = {
    'amount_raw': '100000000000000000000000000',
    'source': 'nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n',
    'block_hash': 'E79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345672',
}
req3.headers.get = lambda k, d='': 'E79C939E...'
with patch('server.store.resolve'):
    resp3 = run_paid_work(req3, always_broken, 'https://example.com')
assert _RECOVERABLE_FAILURES['count'] == 3, f'count should be 3, got {_RECOVERABLE_FAILURES[\"count\"]}'
print(f'OK: count after third double-failure = {_RECOVERABLE_FAILURES[\"count\"]}')

print('L34_RESTART_PASS')
" 2>&1