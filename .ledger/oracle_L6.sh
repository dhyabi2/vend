#!/usr/bin/env bash
# Oracle for L6: payment hash parsing — only valid 64-hex Nano block hashes
# are accepted, arbitrary non-hex strings are rejected without touching RPC.
set -euo pipefail

cd "$(dirname "$0")/.."

VENV="$(cd "$(dirname "$0")/.." && pwd)/.venv"
PYTHON="$VENV/bin/python3"

OUT=$($PYTHON -c "
import os, sys

# --- Test parse_block_hash directly ---
from nano_verify import parse_block_hash

# Valid inputs
assert parse_block_hash('A' * 64) == 'A' * 64, 'bare 64 hex should be accepted uppercased'
assert parse_block_hash(('a' * 64).upper()) == 'A' * 64, 'lowercase should be uppercased'
assert parse_block_hash('a' * 64) == 'A' * 64, 'bare lowercase hex should be accepted'

# Invalid inputs — return None (no exception)
assert parse_block_hash('') is None, 'empty should be None'
assert parse_block_hash('a' * 63) is None, '63 chars should be None'
assert parse_block_hash(('a' * 64) + 'b') is None, '65 chars should be None'
assert parse_block_hash('x' * 64) is None, 'non-hex chars should be None'
assert parse_block_hash('!' * 64) is None, 'punctuation should be None'
assert parse_block_hash('abcdefgh') is None, 'short should be None'

# Base64 JSON payloads (x402 format)
import base64, json
payload = json.dumps({'block': 'A' * 64})
encoded = base64.b64encode(payload.encode()).decode()
assert parse_block_hash(encoded) == 'A' * 64, 'base64 JSON with block key'

payload2 = json.dumps({'hash': 'B' * 64})
encoded2 = base64.b64encode(payload2.encode()).decode()
assert parse_block_hash(encoded2) == 'B' * 64, 'base64 JSON with hash key'

# Base64 with garbage inside
payload3 = json.dumps({'block': 'not-a-valid-hash'})
encoded3 = base64.b64encode(payload3.encode()).decode()
assert parse_block_hash(encoded3) is None, 'base64 with invalid hash should be None'

# Base64 with extra keys, valid hash
payload4 = json.dumps({'block': 'A' * 64, 'type': 'send', 'account': 'nano_...'})
encoded4 = base64.b64encode(payload4.encode()).decode()
assert parse_block_hash(encoded4) == 'A' * 64, 'base64 JSON with additional fields'

# Random non-base64 garbage
assert parse_block_hash('just some random text no base64 no hash') is None
assert parse_block_hash('50chars.....a..................................') is None

print('parse_block_hash: all %d tests passed' % 14)
")

echo "unit: $OUT"

# --- Test server-level rejection: invalid X-PAYMENT format ---
OUT2=$($PYTHON -c "
import os
os.environ.setdefault('VEND_DB', '/tmp/vend_l6_test.db')
os.environ.setdefault('NANO_AGENT_ACCOUNT', 'nano_1test1111111111111111111111111111111111111111111111111111z')
try:
    os.unlink(os.environ['VEND_DB'])
except FileNotFoundError:
    pass
import store
store.DB_PATH = os.environ['VEND_DB']
store._INIT_DONE = False
store.init()

import server
import nano_verify
from starlette.testclient import TestClient
import json

_original_verify = server.verify_payment

def fake_verify_never_called(block_hash, *a, **kw):
    raise AssertionError('verify_payment should not be called for invalid hashes!')

server.verify_payment = fake_verify_never_called

client = TestClient(server.app)

def test_returns_402(desc, headers, expected_error='payment_required'):
    # A bare request (no query input) is what a conformance probe sends, and the
    # free trial (block 33) never applies to it. Query input IS trial-eligible,
    # so this test sends the same header with no query string: the law under test
    # is hash parsing, not trial policy.
    resp = client.get('/api/v1/extract', headers=headers)
    body = resp.json()
    if resp.status_code != 402 or body.get('error') != expected_error:
        print('FAIL %s: status=%s error=%s (expected 402 %s)' % (desc, resp.status_code, body.get('error'), expected_error))
        return False
    print('OK %s: 402 %s' % (desc, body.get('error')))
    return True

all_ok = True

# X-PAYMENT with garbage should get 402 payment_required (extract_payment_block returns None)
all_ok &= test_returns_402('60-char garbage', {'X-PAYMENT': 'z' * 60}, 'payment_required')
all_ok &= test_returns_402('123 chars garbage', {'X-PAYMENT': 'x' * 123}, 'payment_required')
all_ok &= test_returns_402('empty header', {'X-PAYMENT': ''}, 'payment_required')
all_ok &= test_returns_402('punctuation hash', {'X-PAYMENT': '!' * 64}, 'payment_required')

# X-PAYMENT with valid 64-hex but not existing on ledger -> verify_payment would be called
# with the fake_verify_never_called... we need to test that path only with real verify.
# For this test we restore verify for valid-looking hashes and check it returns valid=false
# (block not found on ledger) -> 402 payment_invalid.
server.verify_payment = _original_verify
# Use a nonexistent but valid-looking hash
resp = client.get('/api/v1/extract', headers={'X-PAYMENT': 'F' * 64})
body = resp.json()
print('nonexistent_hash: status=%s error=%s' % (resp.status_code, body.get('error')))
if resp.status_code != 402:
    all_ok = False
    print('FAIL nonexistent hash: expected 402')
elif body.get('error') in ('payment_invalid', 'payment_required'):
    print('OK nonexistent hash: returns invalid payment')
else:
    all_ok = False
    print('FAIL nonexistent hash: unexpected error %s' % body.get('error'))

# Missing header -> 402 payment_required
all_ok &= test_returns_402('no header', {}, 'payment_required')

print('server rejection tests: %s' % ('all pass' if all_ok else 'SOME FAILED'))
assert all_ok, 'server-level hash rejection tests failed'
")

echo "server: $OUT2"

echo "L6_PARSE_PASS"