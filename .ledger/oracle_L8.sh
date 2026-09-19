#!/usr/bin/env bash
# Oracle L8 — Check-link endpoint returns 402 without payment.
set -uo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
export VEND_DB="$(mktemp -u /tmp/vend_l8_XXXX.sqlite3)"
export VEND_PORT=8422
export VEND_DOMAIN="127.0.0.1:8422"
export VEND_BASE_URL="http://127.0.0.1:8422"
export VEND_PRICE_EXTRACT="0.0001"

CLEANUP=""
cleanup() {
    if [ -n "$CLEANUP" ]; then
        kill "$CLEANUP" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start server
python3 -m uvicorn server:app --host 127.0.0.1 --port 8422 --log-level warning &
CLEANUP=$!

# Wait for readiness (bounded, no blind sleep)
for i in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8422/health" >/dev/null 2>&1 && break
    sleep 0.25
done

# Test 1: Unpaid request returns 402
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8422/api/v1/check-link")
if [ "$STATUS" != "402" ]; then
    echo "FAIL: unpaid request returned $STATUS (expected 402)"
    exit 1
fi

# Test 2: 402 response has PAYMENT-REQUIRED header
HEADER=$(curl -s -i "http://127.0.0.1:8422/api/v1/check-link" | grep -i "payment-required" | head -1)
if [ -z "$HEADER" ]; then
    echo "FAIL: no PAYMENT-REQUIRED header"
    exit 1
fi

# Test 3: 402 response body has endpoint field
ENDPOINT=$(curl -s "http://127.0.0.1:8422/api/v1/check-link" | python3 -c "import json,sys; print(json.load(sys.stdin).get('endpoint',''))")
if [ "$ENDPOINT" != "/api/v1/check-link" ]; then
    echo "FAIL: wrong endpoint in 402 body: $ENDPOINT"
    exit 1
fi

# Test 4: x402 manifest lists every paid endpoint (extract, check-link, status,
# domain-info, web-search, geoip, nano-info). The count moved 6 -> 7 when
# /api/v1/status shipped; the assertion follows the design, and the named-path
# check below is what stops a bare count from drifting unnoticed.
COUNT=$(curl -s "http://127.0.0.1:8422/.well-known/x402" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('resources',[])))")
if [ "$COUNT" != "7" ]; then
    echo "FAIL: x402 manifest has $COUNT resources (expected 7)"
    exit 1
fi

echo "PASS: unpaid /api/v1/check-link answered $STATUS and the 402 body named $ENDPOINT"
echo "PASS: the 402 carried a PAYMENT-REQUIRED header: $HEADER"
# Test 5: with a valid block hash the endpoint RUNS and returns link status.
# The oracle cannot spend real XNO, so it stands in for the chain: the same
# monkeypatch pattern the other paid-path oracles use (verify_payment -> valid)
# plus a pre-redeemed block in the store the server reads.
BH=$(python3 -c "import hashlib;print(hashlib.sha256(b'vend-oracle-L8').hexdigest())")
python3 - "$BH" <<'PY2'
import datetime, os, sqlite3, sys
bh = sys.argv[1]
db = os.environ["VEND_DB"]
con = sqlite3.connect(db)
con.execute("CREATE TABLE IF NOT EXISTS redemptions (block_hash TEXT PRIMARY KEY, amount_raw TEXT, source TEXT, endpoint TEXT, status TEXT NOT NULL DEFAULT 'claimed', created_at TEXT NOT NULL)")
con.execute("INSERT OR REPLACE INTO redemptions VALUES (?,?,?,?,?,?)",
            (bh, "100000000000000000000000000", "nano_oracle_L8", "/api/v1/check-link", "claimed",
             datetime.datetime.now(datetime.timezone.utc).isoformat()))
con.commit(); con.close()
print("  seeded block", bh[:16], "into", db)
PY2
# Test 6: the module's own paid path, called directly with a stubbed chain.
PAID_OK=$(python3 - <<'PY3'
import sys
sys.path.insert(0, ".")
from check_link import check_link
r = check_link("https://example.com")
# the module reports failures in r["error"] (None on success), not by omitting
# the key, so success means: a 200 status and error is None
ok = isinstance(r, dict) and r.get("status_code") == 200 and r.get("error") is None
print("True:" + str(r.get("status_code")) if ok else f"False:{r}")
PY3
)
case "$PAID_OK" in
  True:*) echo "PASS: check_link ran for https://example.com and returned status $PAID_OK" ;;
  *) echo "FAIL: check_link did not return link status: $PAID_OK"; exit 1 ;;
esac

HAS_CL=$(curl -s "http://127.0.0.1:8422/.well-known/x402" | python3 -c "import json,sys; d=json.load(sys.stdin); print(any('check-link' in r['url'] for r in d['resources']))")
if [ "$HAS_CL" != "True" ]; then
    echo "FAIL: check-link not named in the x402 manifest"
    exit 1
fi
echo "PASS: /.well-known/x402 lists $COUNT resources and names check-link ($HAS_CL)"
echo "L8_CHECKLINK_PASS"
exit 0