#!/usr/bin/env bash
# Oracle for L30 — the paid rail, proven with real on-ledger money.
#
# L31: A real confirmed Nano send to the quoted payTo address, of at least the
#      quoted price, buys exactly one delivered call over HTTP; the same block
#      is refused on replay.
#
# Why a scratch server: replay protection consumes a block hash, so a law that
# spends a real block once cannot be re-run by the ledger (verify, unwinding,
# mutation runs all re-run it).  The oracle therefore starts its OWN server
# process on a private port with a private, freshly deleted payment DB.  The
# code path exercised is byte-for-byte the one the production server runs
# (server.py + nano_verify.py + store.py); only VEND_DB and VEND_PORT differ.
#
# The block used is a real, confirmed mainnet block that paid the payout address
# on-ledger.  The oracle re-derives its destination and amount from the ledger
# itself before spending it, so the law is grounded in ledger data and not in a
# constant I chose.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PORT="${L30_PORT:-8499}"
TMP="$REPO/.ledger/tmp"
DB="$TMP/l30.sqlite3"
LOG="$TMP/l30-server.log"
PAY_TO="nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"
REAL_BLOCK="B42D35136339688A1E1AA8A5E07F5C95C15A7E806D2EE803D293B3BEE52010FB"
PRICE_RAW="100000000000000000000000000"   # 0.0001 XNO

fail=0
note() { echo "  $*"; }
ok()   { echo "  PASS: $*"; }
bad()  { echo "  FAIL: $*"; fail=$((fail + 1)); }

mkdir -p "$TMP"
rm -f "$DB" "$DB-wal" "$DB-shm"
: > "$LOG"

cleanup() {
    if [ -n "${SRV_PID:-}" ]; then kill "$SRV_PID" 2>/dev/null || true; wait "$SRV_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

echo "L31_ORACLE_START"

# 0. A private server with a private payment DB.
VEND_PORT="$PORT" VEND_DB="$DB" VEND_HOST=127.0.0.1 \
    .venv/bin/python server.py >>"$LOG" 2>&1 &
SRV_PID=$!

up=0
for _ in $(seq 1 40); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health" || echo 000)" = "200" ]; then up=1; break; fi
    sleep 0.25
done
if [ "$up" != "1" ]; then
    bad "scratch server did not come up on :$PORT (see $LOG)"
    tail -5 "$LOG" | sed 's/^/    /'
    echo "L31_ORACLE_FAIL"
    exit 1
fi
ok "scratch server up on 127.0.0.1:$PORT with payment DB $DB"

# 1. Unpaid call quotes a challenge naming the payout address.
CHAL="$TMP/l30-challenge.json"
# 1. a bare probe (no query input) must answer 402 even from a trial-eligible IP:
#    the free trial only applies to calls that carry input (superseded law L7).
# 2. a real mainnet block, re-derived from the ledger, buys exactly one delivered
#    call; the same block is refused on replay.
code=$(curl -s -o "$CHAL" -w '%{http_code}' \
    "http://127.0.0.1:$PORT/api/v1/extract" || echo 000)
if [ "$code" = "402" ]; then ok "unpaid call answers 402"; else bad "unpaid call expected 402, got $code"; fi

if PAY_TO_QUOTED=$(python3 -c "
import json;d=json.load(open('$CHAL'));print(d['accepts'][0]['payTo'])
" 2>/dev/null); then
    ok "challenge quotes payTo $PAY_TO_QUOTED"
else
    PAY_TO_QUOTED=""
    bad "challenge has no accepts[0].payTo"
fi
if [ "$PAY_TO_QUOTED" = "$PAY_TO" ]; then
    ok "quoted payTo is the payout address the treasury holds"
else
    bad "quoted payTo $PAY_TO_QUOTED != $PAY_TO"
fi

# 2. Re-derive the real block from the ledger: destination + amount must
#    genuinely pay the account the server just quoted.
python3 - "$REAL_BLOCK" "$PAY_TO_QUOTED" "$PRICE_RAW" <<'PY'
import json, sys, urllib.request
block, pay_to, price_raw = sys.argv[1], sys.argv[2], int(sys.argv[3])
req = urllib.request.Request(
    "https://rpc.nano.to",
    data=json.dumps({"action": "block_info", "json_block": "true", "hash": block}).encode(),
    headers={"Content-Type": "application/json", "User-Agent": "vend-oracle/1.0"},
)
info = json.loads(urllib.request.urlopen(req, timeout=20).read())
contents = info.get("contents") or {}
amount = int(info.get("amount", "0"))
assert contents.get("type") == "state", f"not a state block: {contents.get('type')}"
assert contents.get("link_as_account") == pay_to, "block does not pay the quoted address"
assert amount >= price_raw, f"block paid {amount} < asking {price_raw}"
print(f"  PROOF: on-ledger {block[:16]}… pays {amount / 1e30} XNO from "
      f"{contents.get('account')} to the quoted address")
PY
if [ $? -eq 0 ]; then ok "real block re-derived from the ledger pays the quoted address"; else bad "real block does not pay the quoted address"; fi

# 3. Spend it: the paid call must be delivered, with a receipt naming the payer.
PAID="$TMP/l30-paid.json"
code=$(curl -s -o "$PAID" -w '%{http_code}' -H "X-PAYMENT: $REAL_BLOCK" \
    "http://127.0.0.1:$PORT/api/v1/extract?url=https://example.com" || echo 000)
if [ "$code" = "200" ]; then ok "paid call answers 200"; else bad "paid call expected 200, got $code"; cat "$PAID" | head -c 300 | sed 's/^/    /'; echo; fi

python3 - "$PAID" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
text = (d.get("text") or d.get("markdown") or d.get("content") or "")
assert isinstance(text, str) and len(text) > 10, f"no extracted text delivered: {list(d)[:8]}"
pay = d.get("payment") or {}
assert pay.get("amount_xno"), "paid response carries no payment amount"
assert d.get("receipt", "").startswith("paid-by-nano_"), f"no payer receipt: {d.get('receipt')}"
print(f"  PROOF: delivered {len(text)} chars, receipt={d['receipt']}, "
      f"payment.amount_xno={pay['amount_xno']}, source={pay.get('source')}")
PY
if [ $? -eq 0 ]; then ok "paid call delivered data and a receipt naming the paying account"; else bad "paid call did not deliver data plus receipt"; fi

# 4. Replay: the same block must not buy a second call.
code=$(curl -s -o "$TMP/l30-replay.json" -w '%{http_code}' -H "X-PAYMENT: $REAL_BLOCK" \
    "http://127.0.0.1:$PORT/api/v1/extract?url=https://example.com" || echo 000)
if [ "$code" = "402" ] && grep -q "already_redeemed" "$TMP/l30-replay.json"; then
    ok "replay of the spent block is refused 402 already_redeemed"
else
    bad "replay expected 402 already_redeemed, got $code $(head -c 120 "$TMP/l30-replay.json")"
fi

# 5. The payment ledger records the call as delivered, with the real payer.
if [ "$(sqlite3 "$DB" "SELECT status FROM redemptions WHERE block_hash='$REAL_BLOCK';" 2>/dev/null)" = "delivered" ]; then
    ok "ledger row for the block is delivered"
else
    bad "ledger row for the block is not delivered: $(sqlite3 "$DB" "SELECT block_hash,status FROM redemptions;" 2>/dev/null | head -3)"
fi
if [ "$(sqlite3 "$DB" "SELECT COUNT(*) FROM redemptions;" 2>/dev/null)" = "1" ]; then
    ok "exactly one redemption recorded for the two calls"
else
    bad "expected 1 redemption, found $(sqlite3 "$DB" "SELECT COUNT(*) FROM redemptions;" 2>/dev/null)"
fi

echo ""
if [ "$fail" -eq 0 ]; then
    echo "L31_PASS: a real on-ledger Nano payment bought one delivered call, and the replay was refused"
else
    echo "L31_ORACLE_FAIL ($fail checks failed)"
    exit 1
fi
