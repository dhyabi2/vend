#!/usr/bin/env python3
"""GitHub archive/thread state checker for Vend. Uses ghapi.py's gh() (token internal).
Usage: gharc.py <op>
  check-gigs   - state of our gigs.sh fork + issues/comment timeline
  notifs       - /notifications (needs token scope)
  repos        - PANDeveloper001 repos with open issues/prs
"""
import sys, json
sys.path.insert(0, '/root/vend/bin')
import ghapi
from ghapi import gh

def main(op):
    if op == 'notifs':
        r = gh('GET', '/notifications?per_page=50')
        print(json.dumps(r)[:3000])
    elif op == 'repos':
        r = gh('GET', '/users/PANDeveloper001/repos?per_page=100')
        if isinstance(r, list):
            for x in r:
                if x.get('open_issues_count') or x.get('fork'):
                    print(x['name'], '| fork:', x['fork'], '| open_issues:', x['open_issues_count'])
        else:
            print(json.dumps(r)[:500])
    elif op == 'check-gigs':
        # find our gigs.sh fork
        r = gh('GET', '/users/PANDeveloper001/repos?per_page=100')
        forks = [x['name'] for x in r if 'gigs' in x['name'].lower()] if isinstance(r, list) else []
        print('candidate forks:', forks)
        for f in forks:
            i = gh('GET', f'/repos/PANDeveloper001/{f}/issues?state=all&per_page=100')
            if isinstance(i, list):
                for iss in i:
                    print(f, '#', iss['number'], '|', iss['state'], '|', iss['title'], '| comments:', iss['comments'], '| updated:', iss.get('updated_at'))
            else:
                print(f, json.dumps(i)[:200])
    else:
        print('unknown op')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'repos')
