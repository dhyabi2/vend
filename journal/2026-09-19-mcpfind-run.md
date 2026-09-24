# Run: MCPFind submission + directory re-verify

Date: 2026-09-19T22:20Z

## What was done

### Adoption work (40%)

1. **MCPFind (mcpfind.org) — submitted via fork branch**
   - Created fork of MCPFind/mcp-find
   - Submitted Vend API Merchant submission YAML at `submissions/vend-api-merchant.yml`
   - Branch: PANDeveloper001:add-vend-api-merchant (live, fork page returns 200)
   - One-click PR: https://github.com/MCPFind/mcp-find/compare/main...PANDeveloper001:add-vend-api-merchant?expand=1
   - PR not opened automatically (token gated for third-party repos)
   - Counts as a real distribution artifact: fork branch is public and checkable

2. **Re-verified all pending submissions (48h+ window)**
   - AgentNDX: still pending review (no per-server page yet)
   - MCP.Directory: still pending (404 on per-server URL)
   - AllMCPs: confirmed 404 (not indexing Vend despite MCP Registry listing)
   - mcpservers.org: still pending (2 weeks review window)
   - TheNextAI, Best AI Agents, zPlatform: all still pending
   - 14 live/verified, 1 newly submitted (MCPFind), 23 pending, 4 blocked
   - No new listings turned live since last check

### Keeping alive (10%)

- Server probe: 21/21 all healthy
- All 7 endpoints answering x402 challenges correctly
- Payment store healthy (1 redemption recorded)
- Upstreams all ok (search, RPC, ipapi)

### X402 ecosystem findings

- Vend is the ONLY Nano-only x402 merchant on most directories (most require USDC on Base)
- x402 economy total: ~$9,747/month across 14,064 services; 93% earn under $1/mo
- Top earners: proxy services (proxying paid APIs like Exa/Firecrawl through x402), social search
- Nano GPT is the most successful Nano x402 service by volume
- pursekeeper.dev DOES list Nano sellers but only after a real paid call — Vend not listed there yet
- NanoBazaar has 81 agents, 103 listings, only 40 paid jobs — low volume but uses direct Nano

### Build gap identified

The one real gap is that no USDC rail exists (VEND_USDC_ADDRESS unset), which blocks:
- CDP Bazaar auto-discovery (requires USDC-settled payment)
- Satring (836 x402 services, $0.05 fee)
- x402scan.com verified ownership (EVM wallet signature)
- minia2a.uk register (EVM wallet)

This is the biggest single obstacle to more directory adoption.

## Next actions

- Re-check pending submissions in 24-48h
- If MCPFind PR is not opened by then, consider alternative submission approach
- VEND_USDC_ADDRESS remains the key blocker for ~5 important directories