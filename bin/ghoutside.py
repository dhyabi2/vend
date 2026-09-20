#!/usr/bin/env python3
"""Find OUTSIDE replies on our fork outreach issues (login != PANDeveloper001)
after 2026-09-19. Prints author, date, snippet."""
import sys, json
sys.path.insert(0, '/root/vend/bin')
from ghapi import gh

ME = 'PANDeveloper001'
CUT = '2026-09-19'

def comments_for(repo, num):
    r = gh('GET', f'/repos/{repo}/issues/{num}/comments?per_page=100')
    return r if isinstance(r, list) else []

def main():
    # candidates: repos with open_issues, prefer forks (outreach)
    r = gh('GET', '/users/PANDeveloper001/repos?per_page=100')
    cands = [(x['name'], x['open_issues_count']) for x in r if x['fork'] and x['open_issues_count']>0]
    # gigs-sh priority (real buyer directory)
    cands.insert(0, ('gigs-sh', 1))
    found = []
    for name, _ in cands:
        iss = gh('GET', f'/repos/PANDeveloper001/{name}/issues?state=all&per_page=100')
        if not isinstance(iss, list):
            continue
        for issue in iss:
            if 'pull_request' in issue:
                continue
            cmts = comments_for(f'PANDeveloper001/{name}', issue['number'])
            for c in cmts:
                author = c['user']['login']
                created = c.get('created_at','')
                if author != ME and created >= CUT:
                    found.append((name, issue['number'], author, created, c['body'][:200]))
    if not found:
        print('NO outside replies after', CUT)
    else:
        for f in found:
            print('---', f[0], '#', f[1], '|', f[2], '|', f[3])
            print('   ', f[4].replace('\n',' ')[:200])

if __name__ == '__main__':
    main()
