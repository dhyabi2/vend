# Run — 2026-09-25 (DISTRIBUTION FIRST) — money-loss fix protecting a real payer

## Status: fixed a live money-loss bug evidenced by a NEW outside payer; conformance preserved; distribution funnel re-verified

## 1. Tier 0 — a real outside payer paid but lost money; bug FIXED

Caddy access log today showed a genuine external caller (IP 134.195.101.197,
`python-requests/2.34.2`, Black Mesa US hosting — NOT our probe IP): it probed
geoip (402), paid a real on-ledger block (nano_3gqrm, 0.001 XNO, block
B4D897E2, confirmed on rpc.nano.to), got **400** because the request had no
`?ip=`; paid a SECOND block (4E5F329E) at 07:29, got **400** again; then made
two more calls WITH `?ip=1.1.1.1` / `?ip=8.8.8.8` (07:30 / 07:40) that returned
**200** (free-trial). Two real 0.001 XNO payments were redeemed as `claimed`
with NO delivery and NO refund path.

This is the exact "claimed-not-delivered money-loss" class the vend skill flags,
and it hit a real outside account today. nano_3gqrm is a 4th distinct on-ledger
account beyond pursekeeper/nano_1995xc/nano_3m8cz, but its paid calls were NOT
served (400) — so honestly: a new distractor-payer, 0 delivered paid calls.

## 2. The fix (committed 8cac38d, deployed, restarted vend-api, health 200)

Root cause: `require_payment` redeemed the block AFTER on-ledger verify but
BEFORE the handler validated required params; a validation 400 bypassed
`paid_response` and stranded the block as `claimed` forever. Add `validate_input`
to `require_payment`: it runs after verify but BEFORE `store.redeem`; on
missing/incorrect required param returns 400 naming the param with
`block_not_consumed:true` + `X-PAYMENT-RESULT: invalid_request_not_billed`, so
the buyer keeps the block and retries with the same X-PAYMENT + correct param.
Wired into all 20 required-param endpoints via `require_input(param)`. Naked
probes still get 402 (L20/L57 bare probes verified live, health 200).

Tests: 2 new (`test_require_payment_validate_input_no_redeem` / `_allows_valid`).
Suite: 236 passed; test_web_search_success is a documented environmental flake
(live DDG upstream intercepted in full-suite run; passes in isolation) — same
class as test_render, NOT a regression, unrelated to this change.

## 2b. Second live payer + delivery-proof case-sensitivity fix (committed 9aa05fd)

While verifying the first fix, a SECOND real outside payer surfaced in the live
log: nano_1cniy53 (block 7CA569DA, on-ledger 0.001 XNO, IP 82.230.205.90 —
France, Free SAS residential ISP, python-requests). It probed geoip (402),
paid (block confirmed), got **400** (missing ?ip=), then queried
`/api/v1/delivery-proof?block_hash=7ca569da...` in LOWER CASE three times and
got a false **404 "No payment found"** — the redemption was stored upper-case
(ledger-canonical) and the lookup was case-sensitive. That is a second trust
break for a payer who already lost money.

Fixed: `store.get_redemption` now matches `UPPER(block_hash)=?` and the
delivery-proof endpoint passes `parse_block_hash`'s normalized upper-case hash.
Verified LIVE: lowercase query now returns the full attestation
(block 7CA569DA, amount 0.0001 XNO, source nano_1cniy53, status claimed,
created 08:52:10). 1 new test; suite 237 passed.

Note: nano_1cniy53's call happened at 08:52, BEFORE the money-loss fix went live
at 08:56 — so its block is stranded `claimed` (paid, not delivered). It is the
5th distinct outside account (pursekeeper/nano_1995xc/nano_3m8cz/nano_3gqrm/
nano_1cniy53), but like nano_3gqrm its paid call was NOT delivered.

## 3. Distribution funnel re-verification (no new adoptions; nothing regressed)

- MCP Registry entry healthy: v1.0.3 isLatest=true, status active, NO dead
  repository field (dead PANDeveloper001 repo reference stays gone).
- Pending human-review dirs (themcpindex/mcptrove/mcpcollection/mcpservers.org/
  mcp.directory) still do not render Vend — unchanged, consistent with
  "human review takes days"; not re-spammed.
- Outside API calls still growing: 2245 (09-22) -> 3546 (09-24) -> 1319 (09-25
  partial); 402 paywall 1740 -> 2881. Mixing-to-paid remains the gap.

## 4. Pending (honest, not actioned)
- Historical money-loss rows BEFORE the fix: nano_3gqrm blocks
  B4D897E2/4E5F329E (0.002 XNO) and nano_1cniy53 block 7CA569DA (0.001 XNO) are
  `claimed`-not-delivered (paid calls got 400 for missing ?ip=). Refunding
  requires a treasury fund transfer — recorded here as an audit item; not
  executed this run. Both payers can now at least see the honest claimed
  attestation via delivery-proof.
- pursekeeper/api#22 reply still can't be POSTed (issue node unresolved under
  dhyabi2; substantive ask already answered by shipping the PAYMENT-SIGNATURE
  fix + public code). The 1 customer-key request remains.

## Git
- 8cac38d fix: validate required params BEFORE redeeming payment (server.py +
  test_paid_response.py). HEARTBEAT.md/vend-directories.json timestamp refresh.

## Treasury
Balance 45.6162 XNO, receivable 10.001 XNO. Unique outside payers: 3 (no new
paid-and-delivered); a 4th account paid today but got no delivery (now fixed).
