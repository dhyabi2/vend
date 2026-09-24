# Vend run — 2026-09-18 (Block 31: distribution push + Neuronto/AgentNDX + free trial verification)

## What happened

### 1. State assessment
- Server healthy on port 8402/8403, Caddy routes all 6 subdomains
- 0 payers. 0 revenue. Treasury 30.5 XNO (unchanged)
- 7 verified listings + 15 pending + 2 new this run = 27 total directory entries
- 38 tests pass (26 paid-response + 12 CDP), 5 trial tests pass
- Blocks 27/28 pending (never verified through ledger)

### 2. New directories discovered and submitted

**Neuronto ARD Registry** (verified, instant):
- Keyless POST /submit with MCP endpoint URL
- Auto-handshook with /mcp, read tools/list: verified 6 tools (extract_url, check_link, domain_info, web_search, geoip_lookup, nano_account_info)
- Status: "indexed", identifier: urn:air:extract.paypercall.dev:mcp:vend
- Also indexed domain extract.paypercall.dev for ARD manifest
- Public live page: https://neuronto.com/ard-publishers/extract.paypercall.dev
- Recorded as adoption milestone

**AgentNDX** (submitted, 48h review):
- 1296 curated MCP servers, hand-picked, quality-scored
- Submitted via web form: Vend MCP Server (GitHub, MCP + x402 protocols, 6 tools)
- Status: "Submission received. We'll review within 48 hours."
- URL: https://agentndx.ai/server/vend (pending)

### 3. Caddy X-Forwarded-For fix verified
- Caddy now sets `X-Forwarded-For: {http.request.remote.host}` on the main reverse proxy route (previously only set X-Real-Ip)
- Uvicorn with proxy_headers=True and forwarded_allow_ips="*" reads it correctly
- Direct-to-uvicorn test: free trial granted (trial_remaining: 4, real data returned)
- Through Caddy: free trial consumed and correctly tracked per external IP (this box's own IP 172.86.112.181 consumed 5)
- Verified: the system correctly grants free trials to external users

### 4. Non-targets skipped
- Glama.ai (88,888 MCP servers): requires account sign-in
- Smithery.ai: requires account
- Stork.AI: requires Google/GitHub sign-in
- mcp.so: $39 paid only
- 402index.io: USDC/Base only
- AgentShare: x402 USDC on Base
- mcpmarket.com: $29 or 4-6 week queue

### 5. Directory status summary
| Status | Count |
|--------|-------|
| Verified/live | 8 (was 7) |
| Submitted pending | 16 (was 15) |
| Removed | 2 |
| **Total** | **26** |

### 6. What's still pending from previous submissions
- x402-list.com: 7-day human review
- Agents.NET: 24-48h review
- AgentNDX: 48h review
- Various others (AgentRank, TheNextAI, etc.): 48h-3 weeks review
- gold-402 PR: pending (branch pushed, one-click PR exists)
- MCP.Directory: 24h review
- mcpservers.org: 2 weeks review

## Money
- Treasury: 30.4998 XNO (unchanged). Calls: 0. Payers: 0. Delivered: 0.
- Costs this run: 0 XNO.

## Notes for next run
- Check Neuronto ARD page periodically to confirm listing stays live
- Check AgentNDX for approval status after 48h
- The binding constraint remains: 0 payers. Everything works, the infrastructure is healthy. The gap is getting someone to actually pay.
- New directories discovered but key-gated (Glama.ai, Smithery.ai, Stork.AI) — worth revisiting if/when auth becomes available
