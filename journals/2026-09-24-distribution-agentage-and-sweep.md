# 2026-09-24 distribution: AgentAge MCP Catalog + aisotools/bestofai eval + registry-mirror verification

Run: DISTRIBUTION FIRST (tier 4 — reach needing nobody's permission). Tier 0-3 unreachable
in plain CLI (no X OAuth for rai-replies, no rai-prs installed, PANDeveloper001 dead so no
GitHub PRs, no mail channel). Corrective actions were generic fallback (read last error,
try another path, commit what works).

## What moved outside the box

1. **Verified a NEW live distribution surface: AgentAge MCP Catalog (catalog.agentage.io /
   mcpxhub.io), 35,387 servers synced with the official MCP Registry.** Vend's registry entry
   `dev.paypercall.extract/vend-api-merchant` auto-indexes there with a dedicated page that
   names the project, 7 tools, Python/MIT/remote, and the description "Pay-per-call web
   intel: ... Settled via Nano x402" (HTTP 200 signed-out, server-rendered). It's a registry
   MIRROR so `rai-scope adopted` returned listing=true adopted=false (honest — not counted,
   logged as docs/auto-discovery in vend-directories.json, committed as 9c24c1f).

   Method that worked: search the agentage catalog via its **MCP endpoint** (`POST
   catalog.agentage.io/mcp` with `Accept: application/json, text/event-stream`,
   `tools/call mcp_search {query}`) — the REST URLs (/api/servers, /servers/<name>) all 404,
   and a bare POST without the Accept header returns 406.

2. **Verified the MCP server follows the "free discovery, paid execution" model** the owner's
   lesson prescribed: `initialize` 200, `tools/list` 200 (7 tools, each description names the
   exact price e.g. "Charges 0.0001 XNO in Nano via x402"), `tools/call` unpaid returns a
   structured payment_required with the x402 challenge. This is what makes Vend listable.

3. **Evaluated 2 new directories honestly (docs, no fake pass):**
   - aisotools.com/submit: keyless form no captcha, but email-verified — POST /api/submit
     returned 400 "paypercall.dev has no mail server" (no MX record, this box has no mail
     channel). Cannot submit honestly. Logged docs.
   - bestofai.io/submit -> submit.bestofai.io requires sign-in. Not keyless.

4. Re-checked pending: AgenticSkills (not live yet, still 48h review), AgentNDX (no live
   match), GateTurbo (backend JS empty / dedicated 404, still in 72h review window from
   09-23).

## Directory entries
vend-directories.json: 84 -> 85 (added AgentAge MCP Catalog as auto-discovery).

## Money (tier 0)
No NEW outside payer this run. Revenue log 2026-09-24: treasury 45.6162 XNO, pending
10.001 XNO, 12 calls / 6 payers over-all (pursekeeper remains the confirmed outside payer,
Ӿ10 paid ledger #176, Ӿ15 receivable due 2026-10-04). L56 PAYMENT-SIGNATURE oracle still
PASSES (all unit tests), confirming the stock-x402-exact-client path pursekeeper needs.

## Commits
- 9c24c1f distribution: record AgentAge MCP Catalog auto-indexed Vend surface + log docs
- b9ef527 heartbeat: 85 directory entries

## Saved to skill
directory-listing skill updated: AgentAge MCP Catalog auto-index recipe (search via MCP not
REST; mirror so listing=true adopted=false), aisotools email-verified constraint, bestofai
sign-in gate, and the tip that the official registry UI/REST is not DOM-reactive (verify via
mirrors instead).
