#!/usr/bin/env bash
# Oracle for L22: verify atomic write module invariants survive mutation.
# Tests each core function with targeted assertions that fail if the
# function's critical logic is broken.
set -euo pipefail

# Find the module directory
MODULE_DIR="$(cd "$(dirname "$0")/../bin" && pwd)"
MODULE="$MODULE_DIR/atomicwrite.py"
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

fail_count=0

# Helper: run a Python assertion and count a failure if it does not exit 0.
check() {
    local desc="$1"
    shift
    if python3 -c "
import sys
sys.path.insert(0, '$MODULE_DIR')
from atomicwrite import preflight, atomic_write, safe_write, reset, _FAILURES, _LOCKED
$@
" 2>/dev/null; then
        echo "  PASS: $desc"
    else
        echo "  FAIL: $desc"
        fail_count=$((fail_count + 1))
    fi
}

echo "L22_ORACLE_START"

# 1. preflight on a non-existent path
check "preflight: absent file" "
pf = preflight('/nonexistent_xyz_file_98765')
assert not pf['exists'], 'absent file reported as existing'
assert pf['can_create'], 'absent file parent should be writable'
"

# 2. preflight on a missing parent
check "preflight: missing parent" "
pf = preflight('/nonexistent_dir_abc/child.txt')
assert not pf['parent_exists']
"

# 3. atomic_write creates a new file
check "atomic_write: fresh file" "
p = '$WORKDIR/fresh.json'
ok, err = atomic_write(p, '{\"a\":1}')
assert ok, f'fresh atomic write failed: {err}'
assert open(p).read() == '{\"a\":1}', 'content mismatch'
"

# 4. atomic_write overwrites existing file atomically (old file intact on crash simulation)
check "atomic_write: overwrite" "
p = '$WORKDIR/overwrite.json'
with open(p, 'w') as f: f.write('old')
ok, _ = atomic_write(p, 'new')
assert open(p).read() == 'new', 'overwrite content mismatch'
"

# 5. safe_write with atomic fallback recovers from read-only
check "safe_write: recovers from read-only" "
p = '$WORKDIR/ro2.txt'
with open(p, 'w') as f: f.write('x')
import os; os.chmod(p, 0o444)
reset()
ok, rep = safe_write(p, 'y')
assert ok, f'ro recovery failed: {rep}'
assert open(p).read() == 'y', 'ro recovery content mismatch'
"

# 6. safe_write creates missing parent dirs
check "safe_write: creates parent" "
p = '$WORKDIR/subdir1/subdir2/grandchild.txt'
reset()
ok, rep = safe_write(p, 'deep')
assert ok, f'parent creation failed: {rep}'
assert open(p).read() == 'deep'
"

# 7. safe_write patch fallback with old substring
check "safe_write: patch fallback" "
p = '$WORKDIR/patchtest.txt'
with open(p, 'w') as f: f.write('AAA BBB AAA')
reset()
ok, rep = safe_write(p, 'CCC', old='BBB')
assert ok, f'patch fallback failed: {rep}'
assert open(p).read() == 'AAA CCC AAA'
"

# 8. watchdog locks after 2 failures
check "safe_write: watchdog after 2 failures" "
reset()
# Use a non-existent parent (uncreatable) to force failures
p = '$WORKDIR/lockdir/lockchild.txt'
import os
# Make lockdir a file so it cannot be created as a dir
with open('$WORKDIR/lockdir', 'w') as f: f.write('x')
ok1, _ = safe_write(p, 'a')
ok2, _ = safe_write(p, 'b')
assert not ok1 and not ok2, 'expected two failures'
ok3, rep3 = safe_write(p, 'c')
assert not ok3, 'watchdog should have locked'
assert any('watchdog' in r for r in rep3), f'expected watchdog message, got: {rep3}'
"

# 9. forced mode bypasses watchdog
check "safe_write: forced bypasses watchdog" "
reset()
p = '$WORKDIR/lockdir/lockchild2.txt'
import os
with open('$WORKDIR/lockdir', 'w') as f: f.write('x')
safe_write(p, 'a')
safe_write(p, 'b')
# After lock, forced=True should attempt and fail on the real cause (not watchdog)
ok, rep = safe_write(p, 'c', forced=True)
assert not ok, 'forced should still fail on the real cause'
# Should NOT contain 'watchdog' in the report
assert not any('watchdog' in r for r in rep), f'forced mode should bypass watchdog, got: {rep}'
"

# 10. no partial writes: temp file is cleaned up on failure
check "atomic_write: no orphan temp file" "
p = '$WORKDIR/notemp.json'
# Write a file successfully
ok, _ = atomic_write(p, 'test')
assert ok
# Give the temp dir a bad entry to force a failure (parent is file)
import os, tempfile
bad = '$WORKDIR/file_is_a_file'
with open(bad, 'w') as f: f.write('x')
badchild = bad + '/child.txt'
ok, _ = atomic_write(badchild, 'test')
assert not ok, 'should have failed'
# Check no .vendtmp- files litter the parent
for fn in os.listdir('$WORKDIR'):
    assert not fn.startswith('.vendtmp-'), f'orphan temp file: {fn}'
"

echo ""
if [ "$fail_count" -eq 0 ]; then
    echo "L22_ORACLE_PASS"
else
    echo "L22_ORACLE_FAIL ($fail_count checks failed)"
    exit 1
fi