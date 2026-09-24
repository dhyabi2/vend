#!/usr/bin/env python3
"""Read GITHUB token, call one GET, print login + rate limit. Token never printed."""
import json, urllib.request, urllib.error, os

tok = None
for name in ('GITHUB_TOKEN', 'GH_TOKEN'):
    v = os.environ.get(name)
    if v:
        tok = v
if not tok:
    with open('/root/.hermes/.env') as f:
        for line in f:
            line = line.strip()
            if line.startswith('GITHUB_TOKEN=') or line.startswith('GH_TOKEN='):
                tok = line.split('=', 1)[1].strip().strip('"').strip("'")
                if tok:
                    break

def gh(method, path):
    req = urllib.request.Request('https://api.github.com' + path, method=method,
        headers={'Authorization': f'Bearer {tok}', 'User-Agent': 'vend-agent',
                 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}

st, u = gh('GET', '/user')
print('status', st)
if st == 200:
    print('login:', u.get('login'))
    print('token type:', u.get('type'))
else:
    print('body:', json.dumps(u)[:300])
