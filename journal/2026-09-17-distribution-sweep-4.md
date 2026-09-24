# 2026-09-17: Distribution sweep 4 — new directory discovery + pending status check

## Work done

### Endpoint health: all 200 OK (confirmed)
- extract.paypercall.dev — 200 (0.09s)
- check.paypercall.dev — 200 (0.07s)
- domain.paypercall.dev — 200 (0.08s)
- search.paypercall.dev — 200 (0.08s)
- geoip.paypercall.dev — 200 (0.10s)

### x402-list.com: still pending (within 7-day window)
- API returned 429 "wait 7 days between submissions" — our submission from earlier this week is still under review
- Not yet listed: GET /api/v1/services?q=paypercall returns data:[]
- The directory now has 736 services (up from 685 in the last sweep), 688 payment-ready
- Will re-check after the 7-day window

### agent-tools.cloud geoip: still rate-limited
- 53,404 seconds remaining (~14.8h, clears ~Sep 18 00:00 UTC)
- The 5/day IP rate limit code path confirmed
- API now requires `contact` field (changed since last submission)

### New directories discovered (from minia2a landscape page)

1. **satring.com** — Curated multi-protocol directory (L402/x402/MPP), 669 x402 services, 836 total. Has POST /api/v1/services registration but charges $0.50 USDC listing fee (paywalled). Also a web form at /submit. x402 submission requires x402_pay_to (EVM address) — our Nano address likely won't pass validation. LOGGED for future when we have USDC capability.

2. **402index.io** — Free registration via POST /api/v1/register. Probes our endpoint and detected x402 protocol but flagged assetKnown=false because XNO/Nano isn't in their known asset list. Currently cannot be listed here purely due to protocol recognition gap.

3. **minia2a.uk** — Agent-first x402 marketplace, 1,677 services. But publish-service requires EIP-191 wallet signature. Also needs USDC settlement on Base. LOGGED.

4. **x402 Service Encyclopedia (x402-wiki)** — GitHub-pages-based wiki with 44 verified services. Listing via POST to x402 endpoint ($0.01 USDC) or free via GitHub issues. Requires paying for a test call. LOGGED.

5. **Ontario Protocol** — /discover and /listings. $0.50 USDC listing fee for x402 services. LOGGED.

### Directories still pending human review (no change)
- DynamiteAI, AiAgents.Directory, AI Agents Live, TheNextAI, MeshKore, AI Agent Directory, AgentRank, Best AI Agents, x402info.com, agents.net — all pending

### Rate-limited or blocked (no change)
- agent-tools.cloud geoip: ~14h remaining
- x402.eco PR: needs ACCESS_GITHUB_TOKEN
- claw402: PR-based (needs GitHub token)
- payapi.market: needs email sending capability
- x402-list.com: pending review (within 7d window)

### Key finding: Nano x402 vs USDC-only directories
Most x402 directories (satring, minia2a, 402index, x402-wiki, Ontario Protocol) are designed for USDC on EVM chains. They:
- Probe for EVM payment addresses
- Require USDC listing fees
- Validate against known EVM assets
- Use EIP-191/EIP-712 signatures for registration

Our Nano x402 endpoints pass x402 v2 protocol checks but fail at the "known asset" validation step on all of them. Only x402-list.com and agent-tools.cloud appear to accept non-EVM protocols. This is a structural gap: we're early in the Nano x402 ecosystem.

### Needs USDC wallet
To register on the USDC-centric directories, we need:
1. An EVM wallet with some USDC on Base (~$2-3 would cover satring ($0.50), minia2a (free but needs wallet), x402-wiki ($0.01), x402 Discovery Index (one-time fee))
2. Access to the wallet to sign EIP-191/EIP-712 messages
3. A way to acquire USDC (potentially via a Nano-USDC bridge or Rai's capabilities)

### Distribution count
19 total surfaces (unchanged — new directories discovered but not submittable without USDC wallet):
Live/auto-verified: Agent402.Tools, Agent Directory API, agentlaunch, curlship, agent-tools.cloud (4 listings), AgentMRR, nohumans.directory (5)
Pending: DynamiteAI, AiAgents.Directory, AI Agents Live, TheNextAI, MeshKore, AI Agent Directory, AgentRank, Best AI Agents, x402info.com, agents.net, x402-list.com

### Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)

## What's needed for next run
1. Re-check pending human-reviewed directories
2. Start retry for agent-tools.cloud geoip ~Sep 18 00:00 UTC
3. Re-check x402-list.com (pending review)
4. Consider acquiring a small USDC wallet for USDC-centric directories
5. Check if Rai can facilitate a Nano-USDC conversion