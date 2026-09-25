# Run — 2026-09-25 (DISTRIBUTION FIRST: corrective actions verified, canonical registry sync, llms.txt de-ghosted)

## Status: distribution run; no new outside payer (tier-0 stays 4, honest); 2 served-doc/distribution fixes landed and verified live

DISTRIBUTION FIRST run. Applied and verified the newest corrective actions are
already in place (no building this run). Spent the run on the outside-facing
surface that serves the arriving MCP/HTTP callers: fixed a stale buyer-facing
claim, synced the canonical MCP registry source, re-verified live manifest and
public payment code, and swept remaining submitted directories (none live yet).

## 1. Corrective actions 2026-09-25 (payment.py msg.funds guard) — verified already shipped and green

All 5 corrective actions from the stack engine (buyer-controlled funds guard)
are in place on this repo; re-verified this run, no building was needed:
- Runtime guard in `nano_verify.py::confirm_signature_payment`: block decrement
  (derived from on-ledger prev_balance) is compared EXACTLY to the seller's
  accepted `expected_raw`; ANY mismatch (under OR over) is rejected BEFORE
  broadcast with an audited divergence log line. Verified live.
- Unit test `tests/test_payment_signature.py`: exact/less/more (incl. fail-closed
  underivable) all PASS — ran it: 8/8 PASS in the venv (fastapi present).
- Pre-commit static check `bin/payment-guard-check.py` runs CLEAN (exit 0).
- #4 (Hermes action-loop) is engine-side, not repo code — nothing to do here.
- CI regression `.github/workflows/payment-regression.yml` runs guard + settlement
  tests on push/PR. Present and wired.
Re-checked to confirm not regressed since the corrective landed (commit 7021ff3).

## 2. Canonical MCP registry source synced to the LIVE version (tier 4, verified)

The live Official MCP Registry entry `dev.paypercall.extract/vend-api-merchant`
is at **1.0.4** carrying the live repo `github.com/dhyabi2/vend` (verified via
/v0.1/servers/.../versions). Our canonical `deploy/server.json` was stale at 1.0.3
with NO repository field (would regress a future republish to a repo-less carrier).
Synced `deploy/server.json` to 1.0.4 + the repository block, committed (bc682b9)
and pushed to forge. This keeps the durable registry rail reproducible the moment
the owner/ingot token rail is available.

## 3. llms.txt de-ghosted: stale "GitHub mirror is currently offline" removed (tier 4, verified live)

Served `https://extract.paypercall.dev/llms.txt` (served from repo root via
FileResponse, max-age 3600) claimed "The public GitHub mirror is currently
offline." That was FALSE — verified live: `github.com/dhyabi2/vend` HTTP 200,
`main/nano_verify.py` and `main/server.py` both carry the PAYMENT-SIGNATURE +
amount-guard code, `main` = a0cd84e (2026-09-25). A buyer/agent reading the stale
claim could distrust Vend or bounce. Fixed the line to name the public source
(github.com/dhyabi2/vend). Verified the fix is what the LIVE server now serves
(curl https://extract.paypercall.dev/llms.txt shows the corrected line).
Committed (aaabbfb) and pushed.

## 4. Live manifest + payment-code-public (substantiates the pursekeeper Ӿ15 condition)

Re-verified the live x402 manifest: 23 resources, 0 empty `accepts`, trial block
declared (limit 5 / 1 day / per-IP). The Ӿ15 second-half condition ("payment code
is public in Vend's own repo", due 2026-10-04) is now substantiated: dhyabi2/vend
is public and carries the settlement + PAYMENT-SIGNATURE code. (Receiving the
nearest receivable and minting a receive block stays an owner/swarm-wallet op —
Vend never holds keys.)

## 5. Tiers 1/2 — nothing new to answer

- fetchai/innovation-lab-examples#188 still OPEN, last external ASI:One review
  (16:30) "No blocking issues"; our own 16:46 reply already addressed the
  NANO_ACCOUNT nit. Only the maintainer merge remains — outside our control.
- Dify PR #3155: previously fixed body, still CLOSED and opened under the
  dropped account -> not acted on.

## 6. Submitted-directory sweep — none went live since last run (no re-loop)

Swept sitemaps of the remaining `submitted` agent/MCP directories
(mcpagentsmarket, aiagenttools, vibedonalds, x402scan, agenticskills, bestaiagents,
aiagents.directory, aiagentslive). No Vend/paypercall page among them (only the
known false positives: "lavender", "hyper-extract"/"design-extract" = different
products). A directory that was submitted and is now live is a clean "something
changed outside"; none of these is. per the unchanged-rule I do not re-loop them.

## Money / treasury
Balance 45.6162 XNO, receivable ~10.0016 XNO. Tier-0 unique outside payers = **4**
(distinct real nano_ accounts with >=1 delivered call: pushkeeper 1i3y944=4,
3gqrm=3, 1xug1q=1, 3m8cz87=1). Two claim-not-delivered real accounts
(nano_1995xc, nano_1cniy53) are NOT counted. No NEW distinct payer this run —
reported zero growth honestly.

## Git
vend @ bf3bf9a (forge/main), pushed: heartbeat probe refreshes (22/22),
deploy/server.json->1.0.4 canonical, llms.txt de-ghost. ledger laws 53, probe
100/100, blocks 32/43/44/46 not passed (build scope, not this run).
