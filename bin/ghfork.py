#!/usr/bin/env python3
"""Fork a third-party repo, enable issues on the fork, and file a disclosed issue.
Uses ghapi.py's gh() (token internal, never printed).

Usage (token is fine-grained; cannot write or comment on third-party repos):
  ghfork.py fork <owner/repo>                         # fork + enable issues on the fork
  ghfork.py issue <fork-owner/fork-name> <title> <body-file|->   # file disclosed issue on the fork
"""
import sys, json
sys.path.insert(0, '/root/vend/bin')
from ghapi import gh

def fork(owner_repo):
    owner, repo = owner_repo.split('/')
    r = gh('POST', f'/repos/{owner}/{repo}/forks')
    if '_error' in r:
        print('fork ERR:', r['_error'], r.get('_body','')[:200]); return
    fork_full = r.get('full_name')
    fork_name = fork_full.split('/')[1]
    print('fork:', fork_full, '| default_branch:', r.get('default_branch'))
    r2 = gh('PATCH', f'/repos/PANDeveloper001/{fork_name}', {'has_issues': True})
    if '_error' in r2:
        print('enable issues ERR:', r2['_error'], r2.get('_body','')[:200])
    else:
        print('issues enabled:', r2.get('has_issues'), '| fork of:', (r2.get('parent') or {}).get('full_name'))

def issue(fork_full, title, body_file):
    if body_file == '-':
        body = sys.stdin.read()
    else:
        body = open(body_file).read()
    r = gh('POST', f'/repos/{fork_full}/issues', {'title': title, 'body': body})
    if '_error' in r:
        print('issue ERR:', r['_error'], r.get('_body','')[:300])
    else:
        print('created:', r.get('html_url'), '#', r.get('number'))

if __name__ == '__main__':
    op = sys.argv[1]
    if op == 'fork':
        fork(sys.argv[2])
    elif op == 'issue':
        issue(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
