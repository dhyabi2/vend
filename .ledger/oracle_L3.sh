#!/usr/bin/env bash
# Oracle for L3: payment verification ACCEPTS a real on-ledger payment (positive
# path) and REJECTS wrong-destination and underpayment — proven against a real
# confirmed Nano block, not a stub.
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

python3 - <<'PY'
import sys
from nano_verify import verify_payment, PRICE_RAW, check_block_exists

# A real, confirmed 0.0001 XNO send block, fetched live from the ledger below.
REAL_BLOCK = "A4F99E93B9375C06CB663311A5B45D5B039FAC862E38A77F9E60804CF0D244AD"
DEST = "nano_3qb8mkzm3qf1thph1dwqsx9n9fpmfycss3gk7fcjqbfbxb6963gn8q47aagg"

# 0. Ground the test in reality: the block must exist on the ledger right now.
info = check_block_exists(REAL_BLOCK)
if not info or "error" in info:
    print("LEDGER_UNREACHABLE or block missing:", info)
    sys.exit(1)
if info.get("confirmed") != "true":
    print("block not confirmed")
    sys.exit(1)
print("grounding: block confirmed=true amount_nano=%s" % info.get("amount_nano"))

# 1. POSITIVE: real block + correct destination + exact amount -> valid.
r = verify_payment(REAL_BLOCK, PRICE_RAW, DEST)
print("positive: valid=%s msg=%s" % (r["valid"], r["message"]))
assert r["valid"] is True, "a real correct payment must be accepted"
assert r["destination"] == DEST, "destination must be the account form, not the hash"
assert r["amount_raw"] == info.get("amount"), "amount must come from the ledger"

# 2. NEGATIVE: real block sent to the wrong destination -> invalid.
r2 = verify_payment(REAL_BLOCK, PRICE_RAW, "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7")
print("wrong_dest: valid=%s" % r2["valid"])
assert r2["valid"] is False, "a payment to another address must be refused"
assert "wrong address" in r2["message"]

# 3. NEGATIVE: real block, amount below the asking price -> invalid.
r3 = verify_payment(REAL_BLOCK, str(10**30), DEST)
print("underpaid: valid=%s msg=%s" % (r3["valid"], r3["message"]))
assert r3["valid"] is False, "an underpayment must be refused"
assert "too small" in r3["message"]

# 4. NEGATIVE: malformed hashes never reach the ledger and never pass.
for bad in ("", "abc123", None):
    rb = verify_payment(bad or "", PRICE_RAW, DEST)
    assert rb["valid"] is False, "malformed hash must be refused"
print("malformed: all refused")

print("L3_PAYMENT_VERIFY_PASS")
PY