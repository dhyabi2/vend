#!/usr/bin/env python3
"""GitHub API helper for Vend distribution work.
Reads the token from /root/.hermes/.env (never prints it), runs one or more
GitHub REST calls given as argv, prints JSON results.
Usage: ghapi.py <method> <path> [json-body-file]
"""
import sys, json, urllib.request, urllib.error

tok = None
with open('/root/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if tok is None and line.startswith('GITHUB_TOKEN='):
            tok = line.split('=', 1)[1].strip().strip('"').strip("'")
        if tok is None and line.startswith('GH_TOKEN='):
            tok = line.split('=', 1)[1].strip().strip('"').strip("'")

def gh(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request('https://api.github.com' + path,
        data=data, method=method,
        headers={'Authorization': f'Bearer {tok}', 'User-Agent': 'rai-agent',
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json'})
    try:
        return json.load(urllib.request.urlopen(req, timeout=40))
    except urllib.error.HTTPError as e:
        return {'_error': e.code, '_body': e.read().decode()[:500]}

if __name__ == '__main__':
    print('token present:', bool(tok))
