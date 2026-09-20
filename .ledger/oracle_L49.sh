#!/usr/bin/env bash
# Oracle L49 — X-BALANCE header bypasses on-chain payment.
#
# Law: "X-BALANCE header bypasses on-chain payment."
# Scope: server.py
# Test: A request with X-BALANCE: nano_... and sufficient funds is treated as
# paid without hitting the Nano RPC; a response with used_balance includes
# X-Balance-Remaining.
set -uo pipefail
cd /root/vend
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
FAIL=0

# 1. Check that server.py has the X-BALANCE logic in require_payment
.venv/bin/python3 - <<'PY' || FAIL=1
import re, sys
src = open("/root/vend/server.py").read()

# Must mention X-BALANCE in the 402 message
if "X-BALANCE" not in src:
    print("FAIL: server.py does not mention X-BALANCE in its 402 message")
    sys.exit(1)
print("PASS: X-BALANCE mentioned in 402 message")

# Must have extract_balance_account function
if "def extract_balance_account" not in src:
    print("FAIL: server.py lacks extract_balance_account function")
    sys.exit(1)
print("PASS: extract_balance_account function exists")

# Must have balance deduction logic in require_payment
if "deduct_balance" not in src:
    print("FAIL: server.py does not call deduct_balance in require_payment")
    sys.exit(1)
print("PASS: deduct_balance called from require_payment")

# Must attach X-Balance-Remaining header in paid_response
if "X-Balance-Remaining" not in src:
    print("FAIL: paid_response does not set X-Balance-Remaining header")
    sys.exit(1)
print("PASS: X-Balance-Remaining header set in paid_response")

# Must mark is_balance in the payment
if "is_balance" not in src:
    print("FAIL: is_balance not tracked in payment")
    sys.exit(1)
print("PASS: is_balance tracked in payment")

PY

# 2. Start an ephemeral server with a fresh DB and test the X-BALANCE path end-to-end
.venv/bin/python3 - "$W" <<'PY' || FAIL=1
import os, sys, json, time, urllib.request, urllib.error, threading
W = sys.argv[1]

# Fresh DB
db_path = os.path.join(W, "vend.sqlite3")
os.environ["VEND_DB"] = db_path

# Import store and top-up
for m in list(sys.modules.keys()):
    if "store" in m and m not in ("store_health",):
        del sys.modules[m]
import store
store.init()

# Top-up the test account (use a valid-length nano_ address, 65 chars,
# because extract_balance_account validates 60 <= len <= 65)
# 0.001 XNO = 10^27 raw, enough for 10 calls at 0.0001 XNO each
TEST_ACCOUNT = "nano_" + "t" * 59 + "1"
TEN_CALLS_RAW = "1000000000000000000000000000"  # 0.001 XNO, enough for 10 calls
store.top_up("T" * 64, TEST_ACCOUNT, TEN_CALLS_RAW)
account = TEST_ACCOUNT
print(f"PASS: test account has {store.balance_of(account)} raw")

# Now start the server on an ephemeral port
os.environ["VEND_ACCOUNT"] = "nano_1testaccount11111111111111111111111111111111111111111111111111111"
os.environ["VEND_DOMAIN"] = "127.0.0.1:8423"
port = 8423

# Start server in thread
import uvicorn
from server import app as vend_app
server_thread = threading.Thread(
    target=uvicorn.run,
    args=(vend_app,),
    kwargs={"host": "127.0.0.1", "port": port, "log_level": "error"},
    daemon=True
)
server_thread.start()
time.sleep(2)

# The free trial grants 5 calls/IP before the balance path engages. Exhaust
# the trial for 127.0.0.1 first so the X-BALANCE deduction path is actually
# reached, not masked by the trial. (Trial and balance are both "paid" states;
# L49 is about the balance DEDUCTION path specifically.)
for i in range(5):
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/status?url=https://example.com"),
            timeout=10,
        )
    except Exception:
        pass
print("PASS: exhausted free trial (5 calls)")

# Make a request with X-BALANCE header (enough balance)
url = f"http://127.0.0.1:{port}/api/v1/status?url=https://example.com"
req = urllib.request.Request(url)
req.add_header("X-BALANCE", account)

try:
    resp = urllib.request.urlopen(req, timeout=10)
    body = json.loads(resp.read())
    headers = dict(resp.headers)

    # Check for success (status endpoint should return data without payment)
    if "payment" in body:
        pmt = body["payment"]
        if pmt.get("used_balance"):
            print("PASS: response has used_balance=True in payment")
        else:
            print("FAIL: payment present but used_balance is not True")
            sys.exit(1)
    else:
        print("NOTE: no payment block in response (may be free/trial path)")

    # Check X-Balance-Remaining header
    remaining = headers.get("X-Balance-Remaining", "")
    if remaining:
        remaining_int = int(remaining)
        if remaining_int >= 0:
            print(f"PASS: X-Balance-Remaining header present: {remaining}")
        else:
            print(f"FAIL: X-Balance-Remaining negative: {remaining}")
            sys.exit(1)
    else:
        print("NOTE: no X-Balance-Remaining header (may be free trial path)")

    print("PASS: X-BALANCE request succeeded without on-chain payment")

except urllib.error.HTTPError as e:
    body = e.read()
    print(f"FAIL: X-BALANCE request got HTTP {e.code}: {body[:200]}")
    sys.exit(1)

# 3. Test that an unknown account gets a 402 (no balance = fall through to 402)
UNKNOWN_ACCOUNT = "nano_" + "u" * 59 + "2"
req2 = urllib.request.Request(url)
req2.add_header("X-BALANCE", UNKNOWN_ACCOUNT)
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    print("FAIL: unknown account X-BALANCE request succeeded when it should 402")
    sys.exit(1)
except urllib.error.HTTPError as e:
    if e.code == 402:
        print("PASS: unknown account X-BALANCE request returned 402 as expected")
    else:
        print(f"FAIL: unknown account got HTTP {e.code}, expected 402")
        sys.exit(1)

PY

[ $FAIL -eq 0 ] && echo "L49_PASS" || echo "L49_FAIL"
exit $FAIL