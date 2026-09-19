#!/usr/bin/env bash
# Oracle for L31 — the money report is honest about who paid.
#
# L30: An internal probe call is reported separately from customer calls: only
#      calls paid from another account count as calls, payers and deliveries.
#
# Background: Vend holds no wallet key, so the one real end-to-end paid call in
# this repo's history is an internal probe that spends a block already sitting
# in the treasury (see oracle_L30.sh).  If the daily money report counted that
# row as a customer, the one number that matters — unique outside payers — would
# be a lie.  This oracle builds a scratch ledger with one probe row and one
# customer row and reads the real reporting command.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

TMP="$REPO/.ledger/tmp"
DB="$TMP/l31.sqlite3"
fail=0
ok()  { echo "  PASS: $*"; }
bad() { echo "  FAIL: $*"; fail=$((fail + 1)); }

mkdir -p "$TMP"

echo "L30_ORACLE_START"

# 1. A scratch ledger: one internal probe row, one genuine customer row.
rm -f "$DB" "$DB-wal" "$DB-shm"
VEND_DB="$DB" .venv/bin/python - <<'PY'
import os, store, uuid
probe = "AA" * 32          # 64 hex chars, a block already in the treasury
customer = "BB" * 32
store.redeem(probe, endpoint="/api/v1/extract", amount_raw="100000000000000000000000000",
             source="nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7")
store.resolve(probe, "probe_internal")
store.redeem(customer, endpoint="/api/v1/extract", amount_raw="100000000000000000000000000",
             source="nano_3customer00000000000000000000000000000000000000000000000000000")
store.resolve(customer, "delivered")
print("  scratch ledger: 1 probe_internal row + 1 delivered customer row")
PY
[ $? -eq 0 ] && ok "scratch ledger built through store.py" || bad "could not build scratch ledger"

# 2. The report must count the customer only.
OUT=$(VEND_DB="$DB" bash bin/revenue-track 2>&1)
echo "  report: $OUT"
for pair in "calls=1" "payers=1" "delivered=1" "probe=1"; do
    case "$OUT" in
        *"$pair"*) ok "report shows $pair" ;;
        *) bad "report is missing $pair" ;;
    esac
done
case "$OUT" in
    *"calls=2"*) bad "report counted the internal probe as a call" ;;
esac

# 3. A ledger holding nothing but probes must report zero of everything.
rm -f "$DB" "$DB-wal" "$DB-shm"
VEND_DB="$DB" .venv/bin/python - <<'PY'
import store
store.redeem("CC" * 32, endpoint="/api/v1/extract", amount_raw="100000000000000000000000000",
             source="nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7")
store.resolve("CC" * 32, "probe_internal")
PY
OUT=$(VEND_DB="$DB" bash bin/revenue-track 2>&1)
echo "  probe-only report: $OUT"
for pair in "calls=0" "payers=0" "delivered=0" "probe=1"; do
    case "$OUT" in
        *"$pair"*) ok "probe-only ledger reports $pair" ;;
        *) bad "probe-only ledger is missing $pair" ;;
    esac
done

echo ""
if [ "$fail" -eq 0 ]; then
    echo "L30_PASS: internal probes are reported separately and never counted as customer calls or payers"
else
    echo "L30_ORACLE_FAIL ($fail checks failed)"
    exit 1
fi
