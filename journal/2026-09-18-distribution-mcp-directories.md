# Distribution run: MCP directories + proxy fix

## What happened

### 1. Production bug fix: free trial system (proxy_headers)
The free trial tracker keys on `request.client.host`, which was always `127.0.0.1` through Caddy proxy.
This meant all external clients shared one 5-call pool and it looked like the trial didn't work.
**Fix:** added `proxy_headers=True` and `forwarded_allow_ips="*"` to `uvicorn.run()`.
**Verification:** `curl -X GET .../extract?url=example.com` now returns real data + `free_trial: True`,
`trial_remaining: 3` (per-IP tracking works).
**Commit:** d1832a2

### 2. New MCP directory listings
Discovered and submitted Vend's MCP server to two major directories:
- **MCP.Directory** (mcp.directory) — 2,303 servers, 1,907 publishers, free review within 24h
  - Submitted: GitHub URL auto-detection, remote MCP at extract.paypercall.dev/mcp
  - Status: submitted, pending review
- **mcpservers.org** (Awesome MCP Servers) — free tier, review within 2 weeks
  - Submitted as remote MCP with no auth, free plan
  - Status: submitted, pending review

### 3. New directories evaluated (not submitted)
- mcp.so: $39 paid only, no free tier → skip
- mcpmarket.com: $29 paid or free queue (4-6 weeks) → pending
- payapi.market: USDC-only → skip
- relai.fi/market: Solana/Base/Ethereum USDC → skip
- agentic.market (Coinbase): USDC only → skip

### 4. Test status
43/43 all pass