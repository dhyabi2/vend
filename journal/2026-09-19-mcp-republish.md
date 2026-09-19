# MCP Registry re-publish (v1.0.2) + Agent402 verification

## Done
- Re-published Vend MCP server to official MCP Registry at v1.0.2
  - Namespace: dev.paypercall.extract/vend-api-merchant
  - `mcp-publisher publish --file server.json` returned ✓ Successfully published
  - Version bumped from 1.0.1 → 1.0.2 to avoid duplicate version error
  - Previous publish was lost in MCP Registry preview data reset
- Verified Vend is registered and routable on Agent402.Tools
  - `POST /api/index/register` returned `{"listed":true, "routable":true, "health":1, "toolCount":7, "networks":["nano:mainnet"]}`
  - This means Vend is on the Agent402 Smart Order Router — buyers can be routed to Vend
- Re-verified Neuronto ARD: 7 tools indexed, MCP endpoint re-checked
- All 6 Vend endpoints healthy (x402 manifest, health, paid endpoints, demo, agent card)
- No new Nano-friendly keyless directories discovered (land-grab still exhausted)

## Pending
- MCPFind PR still unsubmitted (GitHub token 404s for PANDeveloper001/vend; can't create PR from fork branch without working gh CLI or token)
- x402-list.com still in 7-day cooldown
- Pursekeeper listing still needs Rai (no email/gh tool on this box)
- USDC blocker still in place for EVM-required directories
