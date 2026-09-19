#!/usr/bin/env bash
# Oracle L49 — the pre-commit gate refuses a staged secret and lets a clean
# commit through.
#
# Law: "A staged secret name is refused before it enters a commit, and a clean
# commit still lands."  Scope: .githooks/pre-commit, .gitignore.
#
# Runs the real hook in a throwaway repo with the real scanner and rules copied
# from this repo.  No key-shaped fixture is written anywhere: the fixtures are
# two-byte files named like secret files.
#
# Controls, so a gate that refuses everything cannot pass:
#   A. the index layer alone (staged-content check disabled) -> still refused
#   B. the gate replaced by `exit 0` -> the file LANDS, so the refusals above
#      are caused by this gate and not by the environment
set -uo pipefail
REPO=/root/vend
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAIL=0

mkdir -p "$TMP/repo/.githooks" "$TMP/repo/bin"
cd "$TMP/repo" || exit 1
git init -q .
git config user.email oracle@local
git config user.name oracle
git config core.hooksPath .githooks
cp "$REPO/.githooks/pre-commit" .githooks/pre-commit
cp "$REPO/secret_patterns.py" .
cp "$REPO/bin/secret-scan.py" bin/secret-scan.py
chmod +x .githooks/pre-commit

# 1. a staged secret file must be refused
printf 'DEMO=1\n' > .env
git add .env
if git commit -q -m "staged secret" >/dev/null 2>&1; then
    echo "L49_FAIL: a staged .env was committed"
    FAIL=1
else
    echo "ok: staged .env refused"
fi
git reset -q

# 2. the same gate must still let honest work through
printf 'print("ok")\n' > clean.py
git add clean.py
if git commit -q -m "clean commit" >/dev/null 2>&1; then
    echo "ok: clean commit landed"
else
    echo "L49_FAIL: a clean commit was refused"
    FAIL=1
fi

# 3. control A: with the staged-content check disabled, the index layer alone
#    must still refuse it
sed 's/^staged=.*/staged=""/' "$REPO/.githooks/pre-commit" > .githooks/pre-commit
chmod +x .githooks/pre-commit
printf 'DEMO=2\n' > secret.pem
git add secret.pem
if git commit -q -m "control A" >/dev/null 2>&1; then
    echo "L49_FAIL: control A committed a secret name with the staged check disabled"
    FAIL=1
else
    echo "ok: control A refused by the index layer alone"
fi
git reset -q

# 4. control B: a gate that always passes must let the file land, otherwise the
#    refusals above proved nothing about this gate
printf '#!/bin/sh\nexit 0\n' > .githooks/pre-commit
chmod +x .githooks/pre-commit
printf 'DEMO=3\n' > secret2.pem
git add secret2.pem
if git commit -q -m "control B" >/dev/null 2>&1; then
    echo "ok: control B landed the file with a no-op gate (the gate is the refuser)"
else
    echo "L49_FAIL: control B was refused even with a no-op gate"
    FAIL=1
fi

[ $FAIL -eq 0 ] && echo "L49_PASS" || echo "L49_FAIL"
exit $FAIL
