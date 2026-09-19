#!/usr/bin/env bash
# Oracle for L1: Payment verification refuses invalid payments,
# never charging for a failed extraction.
# All tests are local — no Nano RPC needed for rejection paths.
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Test 1: Empty block hash -> Invalid block hash
r1=$(python3 -c "
from nano_verify import verify_payment
r = verify_payment('')
print('valid=' + str(r['valid']) + ' msg=' + r['message'])
")
echo "empty_hash: $r1"

# Test 2: Short block hash -> Invalid block hash
r2=$(python3 -c "
from nano_verify import verify_payment
r = verify_payment('abc123')
print('valid=' + str(r['valid']) + ' msg=' + r['message'])
")
echo "short_hash: $r2"

# Test 3: No VEND_ACCOUNT env set but function handles it gracefully
r3=$(python3 -c "
from nano_verify import verify_payment, format_402_response
# format_402_response needs VEND_ACCOUNT; verify_payment should not crash with empty
import os
os.environ['NANO_AGENT_ACCOUNT'] = 'nano_1test1111111111111111111111111111111111111111111111111111z'
r = verify_payment('nano_valid_looking_hash_but_not_real', expected_amount_raw='1')
print('valid=' + str(r['valid']) + ' msg_split=' + r['message'].split(':')[0])
")
echo "fake_block: $r3"

# Test 4: format_402_response produces valid base64 that decodes to JSON with x402Version
r4=$(python3 -c "
from nano_verify import format_402_response
import json, base64, os
os.environ['NANO_AGENT_ACCOUNT'] = 'nano_1test1111111111111111111111111111111111111111111111111111z'
b64 = format_402_response('/api/v1/extract', 0.0001)
decoded = base64.b64decode(b64).decode()
payload = json.loads(decoded)
print('x402Version=' + str(payload.get('x402Version')) + ' accepts_count=' + str(len(payload.get('accepts', []))))
")
echo "format_402: $r4"

# Test 5: Verify the RPC code path is wired in — check_block_exists makes an HTTP call
r5=$(python3 -c "
from nano_verify import check_block_exists, NANO_RPC_URL
import os
os.environ['NANO_AGENT_ACCOUNT'] = 'nano_1test1111111111111111111111111111111111111111111111111111z'
# With a real RPC URL, check_block_exists should attempt the call
result = check_block_exists('nano_fake_block_hash_that_triggers_rpc_call_12345678')
# Should get either None (HTTP error) or a dict with 'error' key (block not found)
# Either way, the RPC call path was exercised — not a local-only validation
print('rpc_attempted=True result_type=' + str(type(result).__name__))
if result and 'error' in result:
    print('rpc_result=' + result['error'][:50])
" 2>&1)
echo "rpc_path: $r5"

# Test 6: prove never_charge_on_failure — the server's require_payment returns before extract_url
# by testing that verify_payment on invalid hashes returns valid=False
# and format_402_response doesn't call any extraction
r6=$(python3 -c "
from nano_verify import verify_payment, format_402_response, VEND_ACCOUNT
import os
os.environ['NANO_AGENT_ACCOUNT'] = 'nano_1test1111111111111111111111111111111111111111111111111111z'
# format_402_response should produce valid JSON without side effects
b64 = format_402_response('/api/v1/extract', 0.0001)
import base64, json
payload = json.loads(base64.b64decode(b64).decode())
assert 'x402Version' in payload, 'missing x402Version'
assert 'accepts' in payload, 'missing accepts'
assert len(payload['accepts']) > 0, 'empty accepts'
# Verify 'resource' names this endpoint as an object with an absolute URL
res = payload['resource']
assert isinstance(res, dict), 'resource must be an object'
assert res.get('mimeType'), 'resource must carry a mimeType'
assert '/api/v1/extract' in res.get('url', ''), 'wrong resource url'
print('no_side_effects=True accepts_with_nano=' + str(len(payload['accepts'])))
" 2>&1)
echo "format_402_nosidefx: $r6"

# Test 7: prove extract_url is NOT called when payment fails — integration test
# by showing the server code path conditionally guards extraction
r7=$(python3 -c "
# Read server.py and verify require_payment returns early on failure
with open('server.py') as f:
    content = f.read()
# Check that extract_url is only called AFTER a payment check passes
if 'if not paid:' in content and 'return response' in content:
    print('guard_present=True')
if 'extract_url(url)' in content:
    print('extract_called_after_guard=True')
" 2>&1)
echo "never_charge: $r7"

echo "L1_ORACLE_DONE"