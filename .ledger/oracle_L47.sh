#!/usr/bin/env bash
# Oracle L47 — Prepaid balance credits from Nano send (top-up, store-level).
#
# Law: "Prepaid balance credits from Nano send."
# Scope: store.py
# Test: A top-up using a verified replica Nano block_hash credits the sender's
# account and the block cannot be replayed.
set -uo pipefail
cd /root/vend
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
FAIL=0

.venv/bin/python3 - "$W" <<'PY' || { echo "L47_FAIL: python oracle failed"; FAIL=1; }
import os, sys, tempfile
W = sys.argv[1]

# Fresh DB for each run
db = os.path.join(W, "vend.sqlite3")
os.environ["VEND_DB"] = db
for m in list(sys.modules.keys()):
    if "store" in m and m not in ("store_health",):
        del sys.modules[m]

import store
store.init()

# 1. Top-up credits the account
assert store.top_up("A" * 64, "nano_test1", "1000000000000000000000000") is True
bal = store.balance_of("nano_test1")
assert bal == 1000000000000000000000000, f"Expected 1 XNO, got {bal}"
print("PASS: top-up credits account")

# 2. Second top-up adds to existing balance
assert store.top_up("B" * 64, "nano_test1", "500000000000000000000000") is True
bal = store.balance_of("nano_test1")
assert bal == 1500000000000000000000000, f"Expected 1.5 XNO, got {bal}"
print("PASS: consecutive top-ups sum")

# 3. Same block cannot top-up twice (replay protection)
assert store.top_up("C" * 64, "nano_test1", "1000000000000000000000000") is True
assert store.top_up("C" * 64, "nano_test2", "1000000000000000000000000") is False
print("PASS: duplicate block_hash rejected (replay protection)")

# 4. Unknown account reports 0 balance
assert store.balance_of("nano_unknown") == 0
print("PASS: unknown account balance is 0")

print("L47_PASS")
PY
[ $FAIL -eq 0 ] && echo "L47_PASS" || echo "L47_FAIL"
exit $FAIL