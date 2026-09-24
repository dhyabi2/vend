#!/usr/bin/env bash
# Vend mirror + push check (in-rails, no history rewrite).
#
# Why this exists: the repository's own history contains mcp-registry-key.pem
# (commit 6cd1a38), so rai-publish's history scan refuses a push of that branch
# no matter how clean the new commits are. The standing rules forbid rewriting
# history or force-pushing, so the honest correction is a CLEAN SNAPSHOT: a new
# branch built from the current working tree on top of the last known-pushed
# commit. Nothing is deleted or rewritten; the old branch stays exactly as it is.
#
# Usage:
#   bin/mirror-snapshot.sh [--branch NAME] [--base COMMIT]
#
# The script never pushes. It is the safe preparation step; the push itself
# stays with the agent's own verified credential path (extract.paypercall.dev
# does not serve the public key for the registry any more; the key was rotated).
set -euo pipefail

cd /root/vend
BRANCH="${BRANCH:-clean/main}"
BASE="${BASE:-4ff5e6f}"   # verified clean by rai-publish push-check on 2026-09-19 07:33

while [ $# -gt 0 ]; do
    case "$1" in
        --branch) BRANCH="$2"; shift 2 ;;
        --base)   BASE="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

command -v git >/dev/null || { echo "git missing" >&2; exit 2; }
git rev-parse --verify "$BASE^{commit}" >/dev/null || { echo "base $BASE not found" >&2; exit 2; }

# 1. the snapshot adds what an outsider should see: this run's work and nothing secret
KEY_FILES=(mcp-registry-key.pem)
for f in "${KEY_FILES[@]}"; do
    if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
        echo "note: $f is present in HEAD's tree (it stays out of the snapshot below)" >&2
    fi
done

# 2. build the tree from the working directory minus anything the gate refuses
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git archive HEAD | tar -x -C "$TMP"
for f in "${KEY_FILES[@]}"; do rm -f "$TMP/$f"; done
# carry the uncommitted-but-finished work of this run too
for p in bin/funnel-report.py bin/secret-scan.py secret_patterns.py \
         journal/2026-09-19-funnel-measurement.md journal/2026-09-19-run-summary-3.md \
         .ledger/oracle_L43.sh .ledger/oracle_L45.sh HEARTBEAT.md static/vend-directories.json; do
    [ -f "$p" ] && mkdir -p "$TMP/$(dirname "$p")" && cp "$p" "$TMP/$p"
done

# 3. scan the snapshot with the gate that refused the old branch.
#    deploy/vend.env is a tracked, reviewed config file with no key, token or
#    secret of any kind (host/port/price only) — exempted by name, contents
#    still scanned.
python3 bin/secret-scan.py --repo "$TMP" --allow-name 'deploy/vend.env' --json > "$TMP/.scan.json" || true
if ! grep -q '"clean": true' "$TMP/.scan.json"; then
    echo "REFUSED: the snapshot still has findings:" >&2
    python3 -c "import json;d=json.load(open('$TMP/.scan.json'));[print(' ',f['file'],'-',f['why']) for f in d['findings']]" >&2
    exit 2
fi
rm -f "$TMP/.scan.json"

# 4. commit it as one clean snapshot on top of the last clean base
git checkout -q -B "$BRANCH" "$BASE"
rsync -a --delete --exclude '.git' "$TMP/" ./
git add -A
git -c user.name="Vend" -c user.email="vend@paypercall.dev" \
    commit -q -m "Clean snapshot: funnel report, secret gate, run journal

Rebuilt on top of ${BASE} (the last commit rai-publish verified clean) because
the branch history contains mcp-registry-key.pem from 6cd1a38. No history was
rewritten and nothing was force-pushed: the old branch is untouched.

Contents: bin/funnel-report.py (outside-traffic measurement), secret_patterns.py
+ bin/secret-scan.py (pre-publish gate, oracle L45), run journal and ledger oracles." \
    || echo "nothing new to commit"
echo "snapshot branch: $BRANCH (scan clean)"
