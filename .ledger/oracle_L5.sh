#!/usr/bin/env bash
# Oracle for L5: replay protection — a block redeemed once is refused on
# a second call with 402, and no extraction runs.
set -euo pipefail

cd "$(dirname "$0")/.."

VENV="$(cd "$(dirname "$0")/.." && pwd)/.venv"
PYTHON="$VENV/bin/python3"

# --- Test A: store.redeem atomicity (unit test, no server needed) ---
OUT=$($PYTHON -c "
import os, sys
os.environ.setdefault('VEND_DB', '/tmp/vend_l5_test.db')
try:
    os.unlink(os.environ['VEND_DB'])
except FileNotFoundError:
    pass
import store
store.init()

h1 = 'A' * 64
h2 = 'B' * 64

# First call should succeed
a1 = store.redeem(h1, endpoint='/api/v1/extract', amount_raw='1', source='nano_1test...')
assert a1 is True, 'first redeem should return True'

# Second call with same hash should fail
a2 = store.redeem(h1, endpoint='/api/v1/extract', amount_raw='1', source='nano_1test...')
assert a2 is False, 'second redeem should return False'

# Different hash should succeed
b1 = store.redeem(h2, endpoint='/api/v1/extract', amount_raw='1', source='nano_1test...')
assert b1 is True, 'different hash should redeem'

# status_of should return 'claimed' for new
s = store.status_of(h1)
assert s is not None, 'status_of should find the redeemed block'
print('unit claim=OK h1_first=True h1_second=False h2_first=True status=%s' % s)

# Resolve to delivered
store.resolve(h1, 'delivered')
s2 = store.status_of(h1)
assert s2 == 'delivered', 'after resolve status should be delivered'
print('unit resolve=OK')

# count_redeemed
assert store.count_redeemed() == 2
print('unit count=OK')
")
echo "unit: $OUT"

# --- Test B: server integration (TestClient with stubbed verify_payment) ---
OUT2=$($PYTHON -c "
import os, sys
os.environ.setdefault('VEND_DB', '/tmp/vend_l5_test2.db')
os.environ.setdefault('NANO_AGENT_ACCOUNT', 'nano_1test1111111111111111111111111111111111111111111111111111z')
try:
    os.unlink(os.environ['VEND_DB'])
except FileNotFoundError:
    pass
# Ensure store has fresh state
import store
store.DB_PATH = os.environ['VEND_DB']
store._INIT_DONE = False
store.init()

import server
from starlette.testclient import TestClient
import json

# Monkeypatch verify_payment to return valid for any 64-char hash
_original_verify = server.verify_payment
_extract_call_count = [0]
def fake_verify(block_hash, *a, **kw):
    return {
        'valid': True,
        'amount_raw': '100000000000000000000000000',
        'source': 'nano_1test1111111111111111111111111111111111111111111111111111z',
        'destination': os.environ['NANO_AGENT_ACCOUNT'],
        'message': 'Fake verified',
        'block_hash': block_hash,
    }
def fake_extract(url):
    _extract_call_count[0] += 1
    return {'url': url, 'title': 'Test', 'text': 'Hello', 'markdown': '# Hello', 'error': None}

server.verify_payment = fake_verify
server.extract_url = fake_extract

client = TestClient(server.app)

# Call 1: with valid-looking block hash
h1 = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
resp1 = client.get('/api/v1/extract?url=https://example.com', headers={'X-PAYMENT': h1})
print('resp1 status=%s body=%s' % (resp1.status_code, json.dumps(resp1.json())))
assert resp1.status_code == 200, 'first call should succeed'
assert _extract_call_count[0] == 1, 'extract_url should be called once'
body1 = resp1.json()
assert body1.get('text') == 'Hello', 'first call should return content'

# Call 2: same block hash -> should be refused
resp2 = client.get('/api/v1/extract?url=https://example.com', headers={'X-PAYMENT': h1})
print('resp2 status=%s body=%s' % (resp2.status_code, json.dumps(resp2.json())))
assert resp2.status_code == 402, 'second call should be 402'
body2 = resp2.json()
assert body2.get('error') == 'payment_already_redeemed', 'second call should say payment_already_redeemed'
assert _extract_call_count[0] == 1, 'extract_url should NOT be called again'

# Call 3: different block hash -> should succeed
h2 = 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'
resp3 = client.get('/api/v1/extract?url=https://example.com', headers={'X-PAYMENT': h2})
print('resp3 status=%s body=%s' % (resp3.status_code, json.dumps(resp3.json())))
assert resp3.status_code == 200, 'third call with new hash should succeed'
assert _extract_call_count[0] == 2, 'extract_url should be called a second time'

print('server integration=pass')
")
echo "integration: $OUT2"

echo "L5_REPLAY_PASS"