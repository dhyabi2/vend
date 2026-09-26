#!/usr/bin/env bash
# Block 47 oracle: hardened static/vend-directories.json handling.
# L59: load never crashes; recovers from missing/corrupt; quarantine+enrich.
# L60: report generation never raises and always returns a partial string.
set -u
PY=/root/vend/.venv/bin/python
BIN=/root/vend/bin

OUT=$($PY - "$BIN" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from directory_index import load_index, render_report, _enrich_and_quarantine
import tempfile, os, json

def poll_missing():
    d, st = load_index('/nonexistent/path.json', use_git=False)
    assert st['recovered'] is True
    assert isinstance(d.get('listings'), list)
    return 'missing_ok'

def poll_corrupt():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, 'bad.json')
    with open(p, 'w') as fh:
        fh.write('{ nope')
    d, st = load_index(p, use_git=False)
    assert st['recovered'] is True
    return 'corrupt_ok'

def poll_quarantine_enrich():
    mixed = {'listings': [
        {'directory': 'A', 'url': 'https://a', 'status': 'ok'},
        {'url': 'https://no-dir'},
        'not-a-dict',
        {'directory': 'B', 'url': 'https://b', 'status': 'ok', 'name': 'B'},
    ]}
    d, q = _enrich_and_quarantine(mixed)
    assert q == 2, f'quarantine count {q}'
    assert len(d['listings']) == 2
    for l in d['listings']:
        for k in ('directory','url','status','name','note','verified'):
            assert k in l, f'missing {k}'
    return 'quarantine_enrich_ok'

def poll_report():
    r = render_report({'listings': [
        {'directory':'A','url':'u','status':'ok','name':'a'},
        {'directory':'B','url':'u','status':'verified','name':'b'}]})
    assert isinstance(r, str) and r.startswith('# Vend Directory Report')
    assert 'Listings: 2' in r
    assert isinstance(render_report(None), str)
    assert isinstance(render_report(42), str)
    return 'report_ok'

print(poll_missing(), poll_corrupt(), poll_quarantine_enrich(), poll_report())
PYEOF
)

echo "oracle output: $OUT"
case "$OUT" in
  *missing_ok*corrupt_ok*quarantine_enrich_ok*report_ok*) echo "L59_L60_PASS"; exit 0 ;;
  *) echo "L59_L60_FAIL"; exit 1 ;;
esac
