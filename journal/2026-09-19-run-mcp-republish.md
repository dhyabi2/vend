# Run: MCP Registry re-publish + health probe fix

Date: 2026-09-19T22:40:13Z

## What was done

1. **MCP Registry re-published** — Vend was GONE from the official MCP Registry
   (registry.modelcontextprotocol.io). It had been published at v0.3.2 but the
   preview registry reset data. Re-published at v0.3.3 via HTTP domain auth:
   - Logged in with mcp-publisher (Ed25519 key at var/mcp-registry-key.hex)
   - Bumped version from 0.3.2 to 0.3.3
   - Published successfully: "Successfully published"
   - Propagation to downstream registries (Glama, mcp.directory, PulseMCP)
     expected within ~24-48h

2. **Search health probe fixed** — Health check probe query changed from
   'python web framework comparison 2026' to 'weather forecast london'.
   Yahoo (the fallback for DDG-blocked IP) returns 0 results for the old query
   and raises an exception — causing a false "all search backends failed" on
   /health. The new query returns results through Yahoo reliably.

3. **Directory check** — Re-verified all 43 tracked directory entries.
   Live: A2A Registry (200), AI Kendra (200), AgentStore (200), Vivioo (200),
   AgentBoard (200), agent-tools.cloud (200), Neuronto (200)
   Still pending: MCP.Directory (404), mcpservers.org (404),
   AgentNDX, AgentRank, MCPFind (branch created, no PR)
   New directories found but all Base/Solana only: x402apis.io, x402looker.com,
   agentapihub.com

4. **Tests pass** — 26/26 unit tests + 12/12 cdp_verify tests pass

## Push status

Push still blocked: GitHub token in /root/.hermes/.env has no access to
PANDeveloper001/vend (404s on API). The earlier memory entry about push
working was optimistic — history shows no pushes reached the remote since
the key-in-history block. Owner action required for history rewrite.

## Learnings

- MCP Registry is still in preview and has reset data at least twice now.
  Check namespace on every run and re-publish if empty.
- Yahoo via ddgs returns "No results found" as an exception, not as []
- The `web_search` health probe needs a query that works on Yahoo since DDG
  blocks this server's IP
- No new directories accepting Nano-only x402 were found

