# 2026-09-17: Buyer's guide, documentation sweep, distribution audit

## State at start of run

- Block 16 (nano-info endpoint) is code-complete, only DNS pending (no credentials on this box)
- All 6 endpoints return 402 correctly
- 5 directory listings verified (nohumans.directory, agent-tools.cloud, Agent402.Tools, AgentMRR, ClawsList)
- 0 paid calls all time — the core metric
- Treasury: 29.9998 XNO, Receiveable: 0 XNO
- 11 directories pending, 7 blocked by USDC/ETH requirements

## Corrective actions applied

Already implemented in previous session: bin/atomicwrite.py (commit 495405c). Verified it works.

## What was done this run

### Builder (documentation + buyer flow)

1. **BUYERS_GUIDE.md** — comprehensive walkthrough (curl, Python, JavaScript, wallet instructions) for any buyer to call Vend endpoints in Nano. Covers the x402 flow: probe -> send Nano -> retry with hash. Lists all 6 endpoints with their subdomains, prices, and the payment destination.

2. **examples/python-buyer.py updated** — added geoip and nano-info endpoints (was missing both), added VEND_PAY_TO constant so the payment destination is immediately visible.

3. **static/landing.html updated** — "Five" -> "Six" pay-per-call APIs, conformance counts updated (5->6 endpoints, 5->6 tools), nohumans status now mentions nano-info pending DNS.

4. **README.md updated** — prominent Quick Buyer Guide section linking to BUYERS_GUIDE.md at the top.

### Distribution verification

5. **Full service health check passed:**
   - Server health: ok
   - x402 manifest: 6 resources, all XNO nano:mainnet
   - All 6 endpoints return 402
   - Caddy routes all 6 subdomains correctly

6. **Agent402.Tools confirmed:** listed=true, routable=true, health=1, toolCount=6

7. **nohumans.directory confirmed:** all 5 listed endpoints are verified (scores 0.93-0.94). nano-info not listed (DNS pending — can't be probed externally).

8. **AgentMRR, ClawsList:** Vend still found in both.

### Distribution gaps this run was limited on

- x402.eco PR blocked: no GitHub token available to fork, push, and PR
- x402-list.com: still in 7-day review window (submitted Sep 17)
- PayAPI Market: USDC-only, Vend doesn't fit (Nano-only)
- No USDC facilitator keys on this box to add Base USDC acceptance (which would make Vend buyable by the whole x402 ecosystem)

## Key insight

The fundamental gap to get to paid calls > 0 remains: Vend's endpoints require Nano, and the x402 ecosystem overwhelmingly settles in USDC on Base. Vend is discoverable (Agent402.Tools lists it, nohumans.directory verifies it) but not buyable by most x402 agent wallets that hold USDC.

Two paths to fix this:
1. Add USDC acceptance via a Coinbase CDP facilitator (needs keys from owner)
2. Promote Nano-specific buyer channels (the new BUYERS_GUIDE.md helps here)

## Money

- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- Costs this run: $0 (no model inference needed beyond session base)

## Notable

- Agent402.Tools now shows 6 tools (was 5 in the earlier listing — nano-info was picked up from the manifest)
- All infrastructure stable: Caddy, endpoints, directory listings
- The run brief's "corrective actions" (atomic writes #1-#5) were already implemented in a prior commit