# Distribution sweep 2026-09-19 08:00 UTC

## What happened
- Re-verified all 22 pending/suspect directory listings (8 live ones + 14 submitted ones)
- Found 5 new directory targets: AgentALog, MCPFind, Cinderwright Discovery Hub, vend-client PyPI gap, Glama namespace
- AllMCPs confirmed auto-indexed from official MCP Registry → moved to verified/live
- Cinderwright Discovery Hub: already_submitted (Vend queued for indexing)
- Glama namespace dev.paypercall.extract confirmed (title: "MCP Servers by dev.paypercall.extract | Glama") but no servers yet

## Status recap
- 44 total directory entries
- 12 verified/live (A2A Registry, agent-tools.cloud, AgentBoard, AgentStore, Agents.NET, AllMCPs, Neuronto ARD, nohumans.directory, Vivioo x2, Glama namespace)
- 19 submitted/pending review (AgentNDX, AI Agent Tools, AI Agents Live, AI Kendra, AiAgents.Directory, Best AI Agents, BotMarket, Dynamite AI, gold-402, MadeWithStack, MCP Agents Market, MCP.Directory, mcpservers.org, TheNextAI, x402-list.com, Cinderwright, zPlatform)
- 7 blocked (need VEND_USDC_ADDRESS or EVM wallet): Satring, minia2a.uk, Bank of AI, x402scan, 402index.io, 402.ad, x402.nexus
- 5 unverified/docs (401agents.xyz, AgentIndexed, AgentX402, x402register.com, vend-client PyPI gap)
- 1 removed (Agent Directory API — Vend disappeared)

## Key findings
- **MCP Registry may have been reset** (still in preview — warns of data resets). Vend-mcp at 0.3.0 may need re-publishing. 
- **vend-client NOT on PyPI** — name free, self-hosted .whl only. Credential gate blocks PyPI publish until trusted publisher or token obtained.
- **Land-grab of nano-only keyless x402 directories is exhausted** — every remaining directory requires EVM wallet, paid submission, or human sign-in.