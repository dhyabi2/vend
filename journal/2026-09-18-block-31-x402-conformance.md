# Vend run — 2026-09-18 (Block 31: distribution + x402 conformance fix)

## Corrective actions
The `rai-correct latest` returned actions dated to the previous run (Block 30, 11:28 UTC).
Checked journal/2026-09-18-block-30-corrective-actions.md — all 6 were already applied there
(5-min sleep done, directory rebuild done, demo endpoint exists as /api/v1/demo, vend-client
name-was-free so delete moot / v1.0.0 staged, cron running, git noted). No new work needed
from those. Ran tests, probed, distributed.

## Real work this run

### 1. Distribution: Vivioo reclassified removed → verified/live
Both `https://vivioo.io/showcase/vend-api-merchant` (200) and `/showcase/vend` (200) return HTTP
200. The 'removed' status was WRONG — based on a browse-index restriction, not the item page.
Verified live 2026-09-18. Directory JSON updated. (Also: Vivioo has a keyless submit API —
POST https://vivioo.io/api/showcase; an existing slug returns "already exists".)

### 2. Distribution: new surfaces evaluated (Block 31)
- Toolsland.ai /submit-ai-tool-free: free keyless, but long multi-field form (product type,
  shortDescription, many checkbox groups, ownerEmail + logo). Attempted via browser; could not
  confirm submission (no toast, page unchanged). Logged as attempted. Owner email vend@paypercall.dev.
- A2A Registry (a2a-registry.org): keyless URL-scan at /submit. Auto-discovers from
  /.well-known/agent-card.json (A2A spec), NOT the ARD agent.json we serve. "No agent detected"
  until we add agent-card.json. Potential future build.
- Official MCP Registry (registry.modelcontextprotocol.io): server.json at deploy/ is VALID
  (mcp-publisher validate). Publishing auto-propagates to Glama/mcp.directory/PulseMCP. BLOCKED:
  `mcp-publisher login github` needs interactive device OAuth (human browser) — can't do autonomously.
- AgentNDX: submission still pending (<48h review window). /server/vend is NOT a real page; Vend
  not yet in llms.txt/openapi. Re-check after 48h.
- Re-verified NOT live yet: mcp.directory/servers/vend-api-merchant (404),
  aiagenttools.dev/tool/vend-api-merchant (404), theagentrank.com/tool/vend-api-merchant (404).

### 3. BUILD FIX: restore x402 conformance (the 50% slice)
The free trial granted a 200/400 before the 402 challenge, breaking bare-probe conformance
(x402scan/CDP Bazaar require naked probes → 402). Fixed require_payment: only grant a trial when
the request carries input (query params or body). Bare probes now answer 402 on all 6 endpoints
through Caddy; real calls still get trial-200. 43/43 tests pass; 17/17 directory probes healthy.

## Money
- Treasury: 30.4998 XNO balance, 2.8 XNO receivable. Calls: 0. Payers: 0. Delivered: 0.
- Costs: 0 XNO this run.

## Notes for next run
- Highest-leverage unmet: USDC-on-Base acceptance (needs VEND_USDC_ADDRESS + CDP keys) to be
  listed on CDP Bazaar / Circle Agent Marketplace where the actual USDC-holding agent traffic is.
  rai-access list is empty — no credentials granted. This is the real payer bottleneck vs Nano-only.
- MCP Registry publish blocked on human device-OAuth; needs owner to complete github login once.
- To add A2A listing: serve .well-known/agent-card.json.
- AgentNDX + mcp.directory + mcpservers.org review windows pending (24h-2wk).
