# Run 2026-09-19: Health check, directory audit, publish + commit

## What was done

1. Ran the live probe — 21/21 endpoints healthy, all_healthy true. The previous probe had a transient
   20/21 due to a slow endpoint; retry with adequate timeout resolved it.
2. Committed and pushed the heartbeat + probe results (commit 5e60732, pushed via bin/rai-ship.sh).
3. Verified all 6 key live listings still resolve (AI Kendra, AgentBoard, nohumans.directory,
   A2A Registry, agent-tools.cloud, vend-client page) — all 200 OK (A2A had a transient 503 on
   first check, resolved on retry).
4. Checked x402-list.com — their API confirms Nano is NOT a supported network (only EVM chains).
   Changed vend-directories.json entry from `submitted` to `blocked` with a clear reason.
5. Checked agents.net directory — Vend API Merchant is listed there with 3 live dedicated agent
   pages (IDs 226, 228, 247), already marked as `live` in vend-directories.json.
6. Ran tests: 5/5 pass.
7. Confirmed vend-client Python wheel is built (1.0.0) and served from the server.
8. Noted that x402-list.com and other USDC-only directories remain blocked/hybrid-gated.

## Verified directory state

14 live/verified entries (carried forward):
- AI Kendra, AgentBoard, AgentMRR, Agents.NET, AgentStore, Agent402.Tools (indexed)
- A2A Registry, agent-tools.cloud, nohumans.directory, Neuronto ARD, Vivioo
- vend-client (published), Official MCP Registry (published), Vend MCP (live)

19 pending → 18 after x402-list.com moved to blocked. Pending entries are too recent (3-5 days)
to have been reviewed; re-check in 7-14 days.

3 blocked (Bank of AI, minia2a, Satring) + 1 new: x402-list.com (Nano not supported).

## Health
- Probe: 21/21
- Tests: 5/5
- Treasury: ? XNO (check with vend-treasury-check.py)

## Money
- 1 lifetime outside payer (geoip, 0.0001 XNO, confirmed)
- No new revenue this run
- No treasury spend this run

## Open items
- Hybrid USDC rail (VEND_USDC_ADDRESS) — needs owner decision to unblock CDP Bazaar,
  402index, 402.ad, Satring, x402.nexus
- vend-client could be published to PyPI via OIDC trusted publisher — needs repo creation
  on PANDeveloper001/vend-client and owner to configure pending publisher on PyPI
- All pending directory submissions to re-check in ~10 days
- L33/L34 ledger laws scoped to oracle files (already passing — the evidence-budget issue
  was the blocker, not the code itself)
