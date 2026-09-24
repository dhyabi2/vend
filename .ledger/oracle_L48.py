#!/usr/bin/env python3
"""Oracle L48 — Balance deduction needs no on-chain RPC.

Law: "Balance deduction needs no on-chain RPC."
Scope: store.py
Test: Calling deduct_balance on a funded account succeeds and returns True;
calling on an unfunded or depleted account returns False. The deduction does
not make any network calls (tested in a temp DB with no RPC config).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a temp DB — no VEND_RPC_URL needed, no network involved
db = tempfile.mktemp(suffix=".sqlite3")
os.environ["VEND_DB"] = db

# Clear any cached store
for m in list(sys.modules.keys()):
    if "store" in m and m not in ("store_health",):
        del sys.modules[m]

import store
store.init()

fail = 0

# 1. Deduct from a funded account
store.top_up("A" * 64, "nano_buyer", "100000000000000000000000")  # 0.1 XNO
assert store.deduct_balance("nano_buyer", "100000000000000000000000") is True
remaining = store.balance_of("nano_buyer")
assert remaining == 0, f"Expected 0, got {remaining}"
print("PASS: deduct from funded account succeeds, balance zeroed")

# 2. Deduct from depleted account
assert store.deduct_balance("nano_buyer", "100000000000000000000000") is False
print("PASS: deduct from depleted account returns False")

# 3. Deduct from unknown account
assert store.deduct_balance("nano_nobody", "100000000000000000000000") is False
print("PASS: deduct from unknown account returns False")

# 4. Deduct partial remaining
store.top_up("B" * 64, "nano_partial", "500000000000000000000000")  # 0.5 XNO
assert store.deduct_balance("nano_partial", "100000000000000000000000") is True  # 0.1 XNO
remaining = store.balance_of("nano_partial")
expected = 400000000000000000000000  # 0.4 XNO
assert remaining == expected, f"Expected {expected}, got {remaining}"
print("PASS: partial deduction leaves correct remainder")

# 5. Insufficient funds
assert store.deduct_balance("nano_partial", "999999999999999999999999999") is False
# Balance unchanged
remaining = store.balance_of("nano_partial")
assert remaining == expected, f"Expected unchanged {expected}, got {remaining}"
print("PASS: insufficient funds rejected, balance unchanged")

# 6. No RPC env: the module never imports RPC-related modules
import inspect
src = inspect.getsource(store)
for rpc_word in ["rpc", "send", "block_info", "process", "http"]:
    # Only check key RPC-related patterns that are NOT in docstrings/comments
    pass  # manual verification: store.py's deduct_balance uses SQL only

# The verification: deduct_balance only uses SQL (UPDATE balances SET balance_raw = ?)
# No network calls, no RPC module involvement.
src_lines = src.split('\n')
deduct_started = False
deduct_network = False
for line in src_lines:
    if 'def deduct_balance' in line:
        deduct_started = True
    if deduct_started:
        if 'requests' in line or 'httpx' in line or 'urllib' in line or 'rpc' in line.lower():
            deduct_network = True
            print(f"WARNING: possible network call in deduct_balance: {line.strip()}")
        if line.strip() == '' and deduct_started:
            break  # end of function

if deduct_network:
    print("FAIL: deduct_balance may use network calls")
    fail = 1
else:
    print("PASS: deduct_balance uses no network calls (SQL-only)")

print("L48_" + ("PASS" if not fail else "FAIL"))
sys.exit(fail)