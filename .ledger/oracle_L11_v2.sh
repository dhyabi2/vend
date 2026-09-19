#!/usr/bin/env bash
# Oracle L11 v2 — Domain-info module returns valid intelligence or error.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Test 1: valid domain returns expected keys at module level
OUT=$(python3 -c "
import sys; sys.path.insert(0, '.')
from domain_info import domain_info, _clean_domain, _dns_lookup, _ssl_info, _http_headers

# _clean_domain
assert _clean_domain('example.com') == 'example.com', 'clean domain failed'
assert _clean_domain('https://example.com/path') == 'example.com', 'url clean failed'
assert _clean_domain('') is None, 'empty should be None'
print('_clean_domain OK')

# _dns_lookup
dns = _dns_lookup('example.com')
assert isinstance(dns, dict), 'dns must be dict'
print(f'dns keys: {list(dns.keys())}')
print('_dns_lookup OK')

# domain_info main
result = domain_info('example.com')
assert isinstance(result, dict), 'result must be dict'
for key in ('domain', 'dns', 'ssl', 'http_headers'):
    assert key in result, f'missing key: {key}'
assert result.get('error') is None, f'unexpected error: {result.get(\"error\")}'
print('domain_info OK')

# invalid domain
bad = domain_info('not-a-domain')
assert 'error' in bad, 'invalid domain should return error'
print(f'invalid domain error: {bad[\"error\"]}')
print('invalid domain OK')

# empty domain
empty = domain_info('')
assert 'error' in empty, 'empty should return error'
print('empty domain OK')

print('L11_MODULE_PASS')
" 2>&1)
echo "$OUT"
if ! echo "$OUT" | grep -q 'L11_MODULE_PASS'; then
    echo "FAIL: module tests did not pass"
    exit 1
fi
exit 0