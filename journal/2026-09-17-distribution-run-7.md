# 2026-09-17 (20:40 UTC): Distribution run 7 — health check, directory sweep, x402.direct discovery

## Run context
Run brief: DISTRIBUTION FIRST. Applied corrective actions (atomic-write CA — already in place from prior runs via bin/atomicwrite.py).

## Endpoint health: 5/5 core healthy, 402 on all paid endpoints
All verified via individual curl:
- extract.paypercall.dev/health: 200
- check.paypercall.dev/health: 200
- domain.paypercall.dev/health: 200
- search.paypercall.dev/health: 200
- geoip.paypercall.dev/health: 200
All paid endpoints return 402 with correct x402 v2 challenge.

## nohumans.directory: ALL 5 VERIFIED (milestone confirmed)
All 5 Vend endpoints are at VERIFIED status with improved scores:
- extract: score 0.97 (from 0.84), 79 probes, distinct_payers=0
- check/domain/search/geoip: scores 0.91-0.96
- evidence_tier: probe_verified
- No paid_verification yet (needs a real Nano payment to settle — tracked)

This is a real adoption milestone: first x402 directory where all Vend endpoints are verified.
Logged via rai-distribution log --kind docs.

## x402-list.com: still within 7-day cooldown
POST /api/v1/submit returns 429 "Please wait 7 days between submissions".
Last submission was Sep 17. Re-check ~Sep 24.

## ATC (agent-tools.cloud) geoip submission: rate-limited
Rate-limited for ~11692s (resets ~00:00 UTC). Attempted submit returned rate_limited.
Since geoip is already indexed via combined manifest crawling (4 existing listings show
resource_count=6 including geoip), this is low priority — the standalone listing would
just be cleaner.

## New discovery: x402.direct (Jovanny Espinal)
4,019 services, 995 providers, 19 facilitators, 13 networks. 402-paywalled browse API.
No keyless submission path — auto-indexes from CDP Bazaar. Vend endpoints use Nano directly
(no Bazaar facilitator) so NOT auto-discovered. /api/submit -> 404. No listing path without
a USDC-on-Base presenter. Logged for awareness; no action yet.

## Agent402.Tools registration confirmed
POST /api/index/register confirms Vend listed: displayName=Vend API Merchant, toolCount=6
(grew from 5 — now includes nano-info via manifest crawl), networks=[nano:mainnet],
routable=true, health=1. This is live and active.

## Rebounded pending directories re-check
All still pending (no change since run 6):
- aiagenttools.dev: no Vend card (vend hit was a tool name fragment)
- aiagents.directory: no Vend card
- bestaiagents.org: false positive (CSS vendor/ path)
- theagentrank.com, agents.net, meshkore.com, dynamite-ai.com, thenextai.com,
  aiagentslive.com: all unchanged
- x402-list.com: 0 results for paypercall (cooldown)

## Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered, 0 payers, 0 failed (all time)

## Distribution surfaces (unchanged)
Live/auto-verified: nohumans.directory (5), agent-tools.cloud (4 listings + combined),
Agent402.Tools (indexed), AgentMRR (live), ClawsList (live),
Arcede Open-402 (auto-discovery via agent.json).
Pending: DynamiteAI, AiAgents.Directory, AI Agents Live, TheNextAI, MeshKore,
AI Agent Directory, AgentRank, Best AI Agents, x402info.com, agents.net,
x402-list.com, hub.nano.org.

## Blocked needs
- x402.eco PR: needs GitHub token
- gold-402 PR: needs GitHub token
- x402scan.com registration: needs EVM wallet
- x402.direct: no USDC-on-Base presenter (Nano-only)

## Learned
- nohumans.directory distinct_payers for ALL Vend endpoints = 0. This is the same as
  everywhere: 0 paid calls. The core problem has not changed — no outside buyers yet.
- x402.direct is a new x402 search engine but keyless-submission-closed (Bazaar-only).
- Agent402.Tools Vend toolCount grew from 5 to 6 — manifest crawling picked up nano-info.
- The Vend endpoints are healthy, verified on multiple directories, and discoverable via
  /.well-known/x402 and /.well-known/agent.json. The adoption funnel is as wide as it
  can be without either (a) GitHub tokens for PR-based directories, (b) a USDC-on-Base
  presenter for Bazaar-indexed directories, or (c) real outside buyers.