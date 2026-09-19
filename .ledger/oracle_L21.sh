#!/usr/bin/env bash
# Oracle L21 — geoip.py module returns structured IP geolocation data.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Test 1: Valid IP returns structured data
OUTPUT=$(python3 -c "
import json, sys
sys.path.insert(0, '.')
from geoip import geoip_lookup

r = geoip_lookup('8.8.8.8')
if 'error' in r:
    print('FAIL: valid IP returned error:', r['error'])
    sys.exit(1)
keys = ['country', 'city', 'latitude', 'longitude', 'isp', 'org', 'asn', 'asn_name']
missing = [k for k in keys if k not in r]
if missing:
    print('FAIL: missing keys:', missing)
    sys.exit(1)
print('valid_ip: ok')
")

if [ $? -ne 0 ] || [ -z "$OUTPUT" ]; then
    echo "FAIL: valid IP lookup failed"
    exit 1
fi

# Test 2: Empty input returns error
OUTPUT2=$(python3 -c "
import json, sys
sys.path.insert(0, '.')
from geoip import geoip_lookup

r = geoip_lookup('')
if 'error' not in r:
    print('FAIL: empty input did not return error')
    sys.exit(1)
print('empty_input: ok')
")

if [ $? -ne 0 ]; then
    echo "FAIL: empty input test failed"
    exit 1
fi

# Test 3: Invalid IP returns error
OUTPUT3=$(python3 -c "
import json, sys
sys.path.insert(0, '.')
from geoip import geoip_lookup

r = geoip_lookup('999.999.999.999')
if 'error' not in r:
    print('FAIL: invalid IP did not return error:', r.get('status'))
    sys.exit(1)
print('invalid_ip: ok')
")

if [ $? -ne 0 ]; then
    echo "FAIL: invalid IP test failed"
    exit 1
fi

echo "$OUTPUT"
echo "$OUTPUT2"
echo "$OUTPUT3"
echo "L21_MODULE_PASS"
exit 0