#!/usr/bin/env python3
"""Read GITHUB token (never prints it), check pursekeeper threads + all comments."""
import json, urllib.request, urllib.error, os

tok = None
with open('/root/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if tok is None and line.startswith('GITHUB_TOKEN='):
            tok = line.split('=', 1)[1].strip().strip('"').strip("'")
        if tok is None and line.startswith('GH_TOKEN='):
            tok = line.split('=', 1)[1].strip().strip('"').strip("'")

def gh(path):
    req = urllib.request.Request('https://api.github.com' + path,
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

for n in (18, 22):
    st, body = gh(f'/repos/pursekeeper/api/issues/{n}')
    print(f'=== issue #{n} status {st} ===')
    if st == 200:
        print('title:', body.get('title'))
        print('state:', body.get('state'))
        print('created_by:', (body.get('user') or {}).get('login'))
        print('comments:', body.get('comments'))
    else:
        print('err:', json.dumps(body)[:200]); continue
    # comments
    cst, cbody = gh(f'/repos/pursekeeper/api/issues/{n}/comments')
    print(f'comments status {cst}, count {len(cbody) if isinstance(cbody,list) else 0}')
    if isinstance(cbody, list):
        for c in cbody:
            print('---')
            print('by:', (c.get('user') or {}).get('login'), 'at:', c.get('created_at'))
            print((c.get('body') or '')[:600].replace('\n', ' '))
