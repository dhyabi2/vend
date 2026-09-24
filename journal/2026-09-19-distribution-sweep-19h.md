# Distribution sweep 2026-09-19 19:00 UTC — MCPSafe + AgentShare subtargets

## What happened
- Probed all 22 pending/unverified listings — none had gone live since last check
- Re-verified key live listings (A2A, AgentBoard, AgentStore, AI Kendra) all still LIVE
- Confirmed server health: 21/21 endpoints healthy, all upstreams ok, payment store ok
- Ran ledger oracles manually: L35 (free trial), L37/L38 (MCP server), L45 (secret gate), L46 (ledger fixtures) — all PASS

## New submissions (2)
1. **MCPSafe** (mcpsafe.dev) — Security-first MCP directory, keyless POST /api/v1/submissions.
   Submission ID: c514fa00-9335-42bb-8277-87d515523141, status: pending
2. **AgentShare MCP Registry** (agentshare.dev/registry) — curated MCP registry, keyless POST /api/v1/registry/submit.
   ID 37, pending_review, status URL: https://agentshare.dev/registry/status/VD2Vug16Jv0NjtX89hYxTI4aRPRmiMsudWsTT_m_qfo
   Category: data_commerce (their allowed set — Vend's x402 data APIs fit)

## Evaluated but not submitted
- x402looker.com (AgentIndex): static directory, Base/Solana chains only — Nano-only Vend not a fit.
- x402.direct/docs: BASE on Base only.

## Directory index updated
40 -> 42 entries. 14 live/verified, 24 pending, 4 blocked/removed.

## State
- 1 paying customer lifetime (0.0001 XNO, geoip, 2026-09-19T04:00:28Z)
- Treasury ~30.5 XNO + 2.8 XNO pending
- Push still blocked (GitHub credential, request #1 open)

## Next
- Re-check MCPSafe & AgentShare in 24-48h
- Re-check AgentNDX / AgentRank / AI Agent Tools / x402-list pending
