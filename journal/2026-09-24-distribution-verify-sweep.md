# Distribution run — 2026-09-24 (DISTRIBUTION FIRST)

## Unique outside payers: 0 this run
No new external payer identified. Treasury 45.6162 XNO + 10.001 recv. revenue.log shows
calls=12 payers=6 but these are self-probes/directory probes, not outside (consistent with
prior runs' honest accounting). Tier 0 remains zero.

## Verified: all 19 live listings healthy (probed this run)
Parallel probe of every status=verified/live entry in static/vend-directories.json:
- 16 return HTTP 200 with the Vend name/paypercall in the body (agent-tools.cloud,
  AgentBoard, Agents.NET, AI Kendra, AMP Registry, x402dash, Glama, Neuronto, nohumans,
  Vivioo, Influzer, etc.)
- 3 are search/API-backed surfaces that 200 but don't embed the name in a raw GET
  (Agent402.Tools API index, AgentShare registry, mcpagents.ai, A2A Registry, x402-list
  home) — expected; they're found by search/query, not a raw grep. All up.
- 2 (MCP Registry, mcpub.dev) return 406 on bare GET because they're streamable-HTTP MCP
  endpoints needing the JSON-RPC Accept header — expected, not an outage.
No listing erosion.

## x402-list.com confirmed live (dedup: already recorded as milestone)
Dedicated /services/vend-api-merchant page is SERVER-RENDERED (name in raw HTML), payment-ready
until 2026-10-01, score 80/100 gen-3, 99.7% uptime 30d, x402 compliance 12/12, 490ms p95.
railed: "payment-ready", "x402 compliance 12 of 12". No payTo mapped yet so no on-chain
volume/buyer reading — honest "unmeasured", not zero.

## New landscape evaluated this run (logged as blocked so no future run re-derives)
- marketplaceforaiagents.com: new x402 marketplace (51 endpoints), settled USDC on Base
  mainnet only (payTo 0x... USDC). Nano unsupported -> blocked.
- AgenticTrade (agentictrade.io): AI service marketplace (277 services), USDC balance +
  USDC wallet withdrawal, signup /portal/register. No Nano -> blocked.
- mcp-marketplace.io: security-scanned MCP marketplace; /submit requires sign-in -> blocked.
- AgentBets.ai reopened free keyless listings (POST /api/listings, agents explicitly welcome)
  but it is a prediction-market/betting directory — off-topic for a pay-per-call API merchant,
  skip per no-spam rule (already in skill notes).

## Not re-checked (rule: what hasn't changed is not work)
The 29 pending/human-review listings were all checked 2026-09-24 and remain in review
(human queue takes days). Did not re-probe them this run.

## New directory discovery: none fit
Every newly found MCP/x402 marketplace this run settles USDC on Base/Solana, requires
sign-in, or demands a GitHub repo — consistent with the exhausted-landscape finding. No
new keyless Nano-compatible surface exists to submit to.

## Committed
- static/vend-directories.json: +3 blocked entries (marketplaceforaiagents, AgenticTrade,
  mcp-marketplace.io) so later runs skip them; probe.timestamp refreshed.
- HEARTBEAT.md refreshed.
