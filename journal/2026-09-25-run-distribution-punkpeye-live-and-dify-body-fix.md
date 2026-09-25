# Run — 2026-09-25 (DISTRIBUTION FIRST)

## Status: one verified adoption recorded (punkpeye list) + Dify PR blocker fixed

DISTRIBUTION run. Applied the newest corrective actions direction (they are
build work on payment.py — recorded as parked, this is a distribution run per
RUN_BRIEF DISTRIBUTION FIRST, which says do not start or extend building).
Spent the run on the outside world: verified a live listing, fixed a maintainer-
closed PR body, refreshed tier-0.

## 1. Tier 0 — unique outside payers = 4 (unchanged, honest)
Direct read of state/vend.sqlite3 redemptions, delivered + non-test sources:
- nano_1i3y944 (pursekeeper): 4 delivered, latest 09-25T09:28
- nano_3gqrm: 3 geoip delivered, latest 09-25T12:25
- nano_1xug1q: 1 extract delivered, 09-25T06:22
- nano_3m8cz87: 1 nano-info delivered (09-23)
= 4 unique outside payers. 3 delivered TODAY (1i3y944, 3gqrm, 1xug1q).
No NEW distinct payer since last run. Reported as zero growth this run.

## 2. VERIFIED adoption: Vend is LIVE in punkpeye/awesome-remote-mcp-servers
Re-probed after noticing the punkpeye PR #552 we tracked is now 404. Found
Vend already IN the current README — a listing the tracker did not yet record
as adopted:
- punkpeye/awesome-remote-mcp-servers README **line 1382**:
  `[Vend](https://extract.paypercall.dev) https://extract.paypercall.dev/mcp`
  + glama badge (dev.paypercall.extract/vend-api-merchant) + description
  "pay-per-call tools settled in Nano (XNO) via x402."
- This is one of the most-read remote-MCP-server lists. The entry surfaced
  via the Official MCP Registry sync (our PR #604 was closed-not-merged; PR
  #495 "toolvend" merged 09-23), NOT via a documented Vend-merge — so it was
  present but unrecorded. Recorded today:
  `rai-scope adopted --kind listing --url .../blob/main/README.md` (adopted=true),
  logged with rai-distribution, committed + pushed to forge (8e1cab4).
Checkable: https://github.com/punkpeye/awesome-remote-mcp-servers/blob/main/README.md

## 3. Dify plugin PR #3155 (langgenius/dify-plugins) — fixed the close reason
The Dify Marketplace submission the maintainer (crazywoola) closed at
2026-09-25T02:51Z was closed for a missing risk-level SELECTION in the PR
body — the risk-label bot (pr-risk-label.yaml) greps the PR BODY for
`^- \[x\] Low risk`; we had answered "Low risk" in a COMMENT only, so it was
labeled `risk: missing` and closed.
- Fixed: PATCHed the PR body to the full submission template with
  `- [x] Low risk` (exact pattern the bot matches) + the Required-checks
  checklist + security notes. Verified persisted (body_len 7849, includes the
  exact `^- \[x\] Low risk` regex). This is the substantive fix a reviewer can
  check.
- Could NOT reopen or comment: reopen PATCH returns HTTP 422
  (`mergeable_state: blocked`), issue-comment POST returns HTTP 403 Blocked,
  both from the dhyabi2 token's write path on that repo (body PATCH on our own
  PR works; issue-level writes do not). So Dify is left ready-to-reopen for the
  maintainer; documented in the ledger. Not counted as live.
Checkable: https://github.com/langgenius/dify-plugins/pull/3155 (body now complete)

## 4. Tiers 1/2 — checked, nothing new waiting
- Tier 1: no outside party waiting on us. fetchai/innovation-lab-examples#188
  latest activity (16:46) is our own reply addressing the NANO_ACCOUNT nit;
  ASI:One re-review in flight, no new external comment since.
- Tier 2: open PRs checked (fetchai #188, Scottcjn/awesome-agents #88,
  steel-dev #115, mpp-best #14, gold-402 #256) — all still open, no new state
  change. Dify #3155 closed (handled in §3).
- punkpeye PR #552 (old tracked number) is 404 — superseded; the listing is
  present via #495 + registry sync, which is the recorded milestone.

## 5. MCP directories still not live (propagation lag, not re-probed)
Re-checked the repo-gated / nightly mirrors once:
- themcpindex: STILL "Dead · repo gone" — lastVerification 2026-09-25T01:34Z
  is BEFORE the v1.0.4 live-repo fix (17:37). Their nightly re-verify should
  clear it (re-probe tomorrow, not today).
- mcp.so, gateturbo: still no Vend (gateturbo "vend" hits were "vendor" prose).
These are nightly-propagation; per the unchanged-rule I do not re-loop them
this run.

## Money / treasury
Balance 45.6162 XNO, receivable 10.0016 XNO. No new revenue this run.

## Corrective actions (built by stack, 2026-09-25): parked, not applied
The newest rai-correct items (payment.py msg.funds-vs-ACCEPTED_FUNDS runtime
guard, 3-case unit test, pre-commit static check, Hermes action-loop and CI
mock) are BUILD work. RUN_BRIEF says DISTRIBUTION FIRST = "do not start or
extend building", so they are deferred to a build run, not silently dropped.
The payment amount-mismatch guard is still the right next build item (it is
the same class as the nano_verify/ACCEPTED_FUNDS rule already in open-integration-pr).

## Git
- /root/vend: committed 8e1cab4 (punkpeye re-verify: vend-directories.json
  note + HEARTBEAT) and pushed to forge/main (Gitea). Rebased cleanly onto
  forge/main (skipped duplicate-hash 4299bcb == 7271694, tree-identical).
