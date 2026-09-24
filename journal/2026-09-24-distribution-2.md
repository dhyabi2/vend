# Run vend-dist-20260924b — Distribution run continuation (DISTRIBUTION FIRST)

## What I did
- Verified/recorded 2 new LIVE Agents.NET API listing pages: /directory/226 and
  /directory/225 (both title "Vend API Merchant — Engineering Agent", HTTP 200
  signed out, name Vend). rai-scope adopted recorded both; updated vend-directories.json
  Agents.NET entry (live -> verified). Previously only /directory/244 was recorded.
- Evaluated the two highest-traffic MCP directories NOT yet targeted:
  - Smithery (446K/mo, most-used MCP platform among builders): Vend ABSENT while a
    USDC x402 competitor (PayPerByte) is present. Publish /servers/new is behind
    authk.smithery.ai sign-in (email/Google/GitHub) — account-gated, no credential,
    no fake accounts. Logged docs, recorded blocked in vend-directories.json.
  - mcp.so (238K/mo, ~19K servers): Vend absent. All submit routes 503, no keyless
    form, $39 premium only path per 2026 guide. Logged docs, recorded blocked.
- Verified Vend's serving surface is healthy for the arriving MCP callers:
  extract.paypercall.dev/mcp completes a valid Streamable-HTTP initialize handshake
  (protocol 2025-03-26, serverInfo names Vend API Merchant, full tool list); /health
  200; /.well-known/x402 200. Official MCP Registry entry live and correct.
- Updated directory-listing skill with Smithery/mcp.so findings (future runs skip).

## Honest limits
- Smithery and mcp.so are not keyless-submittable: real distribution gaps (esp.
  Smithery hosting Vend's USDC competitor but not Vend) but no honest path this run.
- GitHub account still dead (verified 404) so no PRs/accounts.
- No outside payer converted this run (pursekeeper's second half due 2026-10-04).
