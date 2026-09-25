# 2026-09-25 distribution: Vend submitted to AllMCPs + flagship listing health re-verified

Run: DISTRIBUTION FIRST (tier 4 — reach needing nobody's permission). Tiers 0-3 as
reported this run: pursekeeper remains the one confirmed unique outside payer (+10 XNO,
receivable 10.001 XNO). Tiers 1-2 unreachable in plain CLI (no rai-prs, no X OAuth for
rai-replies, no write token for pursekeeper/api#22). Tier 3 needs GitHub write or a mail
channel (both absent, PANDeveloper001 dead). Corrective actions (soft-fail/rai-safe-run,
2026-09-25 00:10) were already shipped and verified in the previous run; this run used them.

## What moved outside the box (checkable)

1. NEW KEYLESS LISTING: Vend submitted to AllMCPs.com (allmcps.com) via their public
   agent API `POST /api/v1/submit` — no account, no captcha, programmatic, accepts a
   REMOTE hosted MCP URL (fits a GitHub-less server). Accepted id=vend-api-merchant,
   status pending, category Search & Data Extraction. The directory already lists x402
   paid-API competitors (ImagePay MCP, x402-sms) — it is a surface buyers exploring
   paid MCP APIs already look. https://allmcps.com/mcp/vend-api-merchant (pending page
   renders empty until review). Logged rai-distribution listing_submitted; NOT counted
   as an adopted milestone until a public page names the project.

2. FLAGSHIP LISTING HEALTH RE-VERIFIED (all HTTP 200 signed-out, unchanged/healthy):
   mcpi.app/servers/vend-api-merchant, catalog.agentage.io/mcp/dev-paypercall-extract-vend-api-merchant,
   checkmcp.dev/mcp/extract-paypercall-dev (Grade A 92), x402-list.com/services/vend-api-merchant.

3. NOT-LIVE CONFIRMED (accurate block, no false pass): mcp.so search "paypercall" = 0
   results (SSR JSON total:0; account-gated submission); GateTurbo search "paypercall"
   = 0 / "vend" matches other servers; wmcp.sh POST /api/v1/directory/submit still 500.

## Money (tier 0)
No NEW outside payer this run. Treasury 45.6162 XNO, receivable 10.001 XNO; pursekeeper
+15 credit due 2026-10-04 (probe + code-public condition, code public at
github.com/dhyabi2/vend a0cd84ee). Unique confirmed outside payers: 1 (pursekeeper).
(Revenue log raw counters calls=12/payers=6/delivered=5 include our own + directory
probe traffic flagged in the run brief — not counted as outside payers.)

## Directory entries
vend-directories.json: 90 -> 91 (added allmcps.com, status submitted).

## Commits
- 9c6a42a distribution: submit Vend to AllMCPs.com (keyless agent API), re-verify
  flagship listings healthy (mcpi/agentage/checkmcp/x402-list all 200), mcp.so+
  gateturbo confirmed not-live

## Saved to skill
directory-listing: added AllMCPs.com section (keyless agent API for remote MCP URLs,
schema, search-first, pending-verify rule, claim needs email-verified token = can't on
this box).
