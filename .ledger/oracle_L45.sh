#!/usr/bin/env bash
# L45 oracle: the pre-publish secret gate refuses a leaked key and passes a clean artifact.
#
# The gate exists for one rule: nothing goes public without a clean scan. On
# 2026-09-19 the repository's own HEAD could not be pushed because an earlier
# commit (6cd1a38) had added mcp-registry-key.pem. That is the failure this
# oracle reproduces, in miniature, in a scratch directory.
#
# The dummy key and token are assembled at runtime so this test file itself does
# not trip the scan it is testing.
set -uo pipefail
cd /root/vend

W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT

fail() { echo "FAIL: $1"; exit 1; }

# 1. a clean snapshot passes
mkdir -p "$W/clean/pkg"
cat > "$W/clean/pkg/client.py" <<'PY'
API = "https://extract.paypercall.dev/api/v1/extract"
def price(): return 0.0001
PY
out=$(python3 bin/secret-scan.py --repo "$W/clean" --json 2>&1)
echo "$out" | grep -q '"clean": true' || fail "clean snapshot was refused: $out"

# 2. a leaked private key in the snapshot is refused
mkdir -p "$W/dirty"
python3 - > "$W/dirty/mcp-registry-key.pem" <<'PYKEY'
BEGIN = "-----BEGIN " + "PRIVATE KEY-----"
END = "-----END " + "PRIVATE KEY-----"
print(BEGIN)
print("MC4CAQAwBQYDK2VwBCIEIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
print(END)
PYKEY
out=$(python3 bin/secret-scan.py --repo "$W/dirty" --json 2>&1)
echo "$out" | grep -q '"clean": false' || fail "leaked key snapshot was NOT refused: $out"
echo "$out" | grep -q 'mcp-registry-key.pem' || fail "refusal did not name the leaked file"

# 3. a secret that only appears inside a built wheel is refused
mkdir -p "$W/whl/vend_client"
python3 - > "$W/whl/vend_client/client.py" <<'PYTOK'
print('TOKEN = "' + "ghp_" + "0123456789abcdefghijklmnopqrstuvwx" + '"')
PYTOK
( cd "$W/whl" && python3 -c "
import zipfile
z=zipfile.ZipFile('$W/bad.whl','w')
z.write('vend_client/client.py','vend_client/client.py')
z.close()" )
out=$(python3 bin/secret-scan.py --repo "$W/bad.whl" --json 2>&1)
echo "$out" | grep -q '"clean": false' || fail "wheel with a github token was NOT refused: $out"
echo "$out" | grep -q 'github token' || fail "wheel refusal did not name the pattern"

# 4. the real release wheel is clean
out=$(python3 bin/secret-scan.py --repo dist/vend_client-0.1.0-py3-none-any.whl --json 2>&1)
echo "$out" | grep -q '"clean": true' || fail "the real release wheel was refused: $out"

# 5. the tracked tree names the known historical leak (regression memory)
out=$(python3 bin/secret-scan.py --repo /root/vend --tree --json 2>&1)
echo "$out" | grep -q 'mcp-registry-key.pem' || fail "tree scan no longer flags the tracked key"

echo "PASS: gate refuses leaked key (file and wheel), passes clean snapshot and the release wheel"
echo "L45_SECRET_GATE_PASS"
