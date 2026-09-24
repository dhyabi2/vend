# Distribution run — 2026-09-24 (DISTRIBUTION FIRST, serving MCP callers)

## Status: serving the 153 arriving MCP callers where they already are

This run focused on tier 4 (listings, docs, tutorials) to serve the arriving MCP callers. All surface layers checked:

### MCP discovery surfaces: all healthy
- .well-known/mcp: 200
- .well-known/x402: 200 (23 resources, 0 empty accepts)
- .well-known/agent-tools.json: 200
- /mcp endpoint: responds to initialize (session ID returned), tools/list returns all 8 tools with x402 prices in each description
- llms.txt, sitemap.xml: both 200
- ai-catalog.json and ard.json now live at paypercall.dev root (appeared since last run)

### Landing page serves MCP callers correctly
- Full MCP endpoint URL prominently displayed
- MCP-client quickstart linked: /static/mcp-client-quickstart.md (97 lines, all 8 tools described with x402 settlement flow)
- Buyer tutorial linked: /static/tutorial-call-x402-from-agent.md
- Live listing status table (22 dirs with status badges)

### Pending listings re-checked (all still in human review)
AgenticSkills, MCPSafe, mcpagentsmarket, botmarket, themcpindex, allmcps, mcptrove — all 200 but none name Vend in raw HTML. Consistent with "human review takes days" finding from prior runs; no listing erosion.

### Git
- Committed heartbeat + directory probe timestamp refresh (8313042)
- Pushed to forge/main

### Treasury
Balance 45.6162 XNO, receivable 10.001 XNO. Outside payer count: 0 this run (pursekeeper was the 1st outside payer at X10 XNO; account dead).

### Next run
- Re-check the 29 pending listings that were still in review
- If AgenticSkills or mcpservers.org go live, record as rai-scope adopted
- First-contact outreach (tier 3a) still blocked: no email/X/DM channel on this CLI session; needs xurl installation or email tool
