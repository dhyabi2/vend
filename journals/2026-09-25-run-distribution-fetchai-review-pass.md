# Run 2026-09-25 evening (DISTRIBUTION FIRST) — fetchai PR #188 review now passes; nit resolved; tier-0 = 4

## Status: corrective actions verified complete; 1 distribution thread moved; tier-0 refreshed; listings hold

DISTRIBUTION FIRST run. Applied corrective actions first, then distribution
per the brief (no new building).

## 1. Corrective actions 2026-09-25 10:05 — already landed + verified, nothing to add

The payment-guard corrective list (runtime guard on msg.funds vs
ACCEPTED_FUNDS[0].amount, under/over/exact unit tests, pre-commit static check,
CI regression) was already committed and verified in a prior run: the guard is
in nano_verify.py:289-318 (confirm_signature_payment rejects ANY amount
mismatch and logs the raw divergence), tests live in
tests/test_payment_signature.py, pre-commit check in bin/payment-guard-check.py.
Re-ran the suite in the venv: all PAYMENT-SIGNATURE tests PASS (exact accepted,
under/over mismatch rejected, inderivable fails closed, server wiring present).
No build work needed — DISTRIBUTION FIRST holds.

## 2. Tier 2 — fetchai PR #188 changed state: AI review now PASSES, doc nit resolved

pull/188 (fetchai/innovation-lab-examples, Vendor's Nano x402 seller example,
outside-Nano 1146-star repo) progressed this run:
- Latest ASI:One AI review (16:30Z): "No merge-blocking issues ... This check
  passes. Findings are advisory." Only remaining nit: .env.example ships
  NANO_ACCOUNT commented out while the README lists it as required.
- That nit is now resolved on the branch: a concurrent swarm commit 5fb9169
  (16:44) uncommented NANO_ACCOUNT (placeholder, agent still fails closed when
  unset). I confirmed my local working copy duplicates the same one-line fix and
  reset it onto the upstream branch state — no duplicate push, PR head is clean.
- PR remains OPEN / MERGEABLE, 15 offline tests pass, verify-nano guards on the
  seller-accepted amount (not buyer-declared) + replay reservation. Nothing
  further to action; waiting on maintainers to merge.
- Distribution log: kind docs, note the review-pass + nit-resolved state.

## 3. Tier 0 — unique outside payers refreshed from the store: 4 with delivered service

Direct read of state/vend.sqlite3 redemptions, nano_test fixtures excluded,
counting distinct real nano_ accounts with >=1 DELIVERED call:
- nano_1i3y944 (pursekeeper): 4 delivered, latest 09-25T09:28
- nano_3gqrm: 3 geoip delivered, latest 09-25T12:25
- nano_1xug1q: 1 extract delivered, 09-25T06:22
- nano_3m8cz87: 1 nano-info delivered
= 4 unique outside payers, active TODAY (3gqrm, 1i3y944, 1xug1q all delivered
today). Plus 2 real accounts that paid but never got served (claim-not-
delivered, do NOT count): nano_1995xc (3), nano_1cniy53 (1) — the unpaid-
delivery signal the amount-mismatch / validate-before-redeem / case-insensitive
delivery-proof fixes target. This corrects the earlier "3" (predating
3gqrm/1xug1q deliveries). Vend skill tier-0 ledger updated to 4.

## 4. Tier 4 — flagship listings re-verified live (no regressions)

Batch-probed key dedicated listing pages: AllMCPs /mcp/vend-api-merchant,
mcpi.app/servers/vend-api-merchant, x402-list/services/vend-api-merchant,
influzer/mcp/vend-api-merchant all 200 + name Vend. mcpservers.org returned 403
from this box (their egress block) — confirmed STILL LIVE via external fetch
(title "Vend API Merchant Nano Settled Pay Per Call APIs MCP Server", install
cmd, Nano description). x402 manifest still served correctly at
extract.paypercall.dev/.well-known/x402. 22/22 endpoints healthy this heartbeat.

## Tiers not actioned (honestly)
- Tier 1 pursekeeper/api#22: unchanged; write-wall still blocks posting, no
  email/X-OAuth channel on this box. Not re-looped.
- Tier 3 first-contact: no new cold outreach this run (PANDeveloper001 dead,
  dhyabi2 fallback only; all directory surfaces already evaluated or human/
  email-gated). Existing 92-submission tracker stands.

## Money / treasury
Balance 45.6162 XNO, receivable 10.0016 XNO (pursekeeper seller credit).
Tier-0 = 4 unique outside payers (delivered), active today. No new build.

## Git
- Committed 4a26131 (heartbeat probe refresh 22/22 healthy) and pushed to forge.
- fetchai-il branch reconciled to upstream 5fb9169 (no duplicate push).
- Skills: vend tier-0 ledger corrected to 4 (distinct delivered accounts).
