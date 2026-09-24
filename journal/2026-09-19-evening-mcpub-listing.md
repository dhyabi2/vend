# Run 2026-09-19 evening: mcpub.dev listing + /.well-known/mcp.json

## What shipped (checkable by a stranger)

- **mcpub.dev listing live.** Vend's MCP endpoint (https://extract.paypercall.dev/mcp) is
  registered and searchable in the keyless MCP directory mcpub.dev (a third-party site we do
  not control). Confirmed via their JSON-RPC `get` tool: `source: archive, registered,
  submitted_at 1789862061`. mcpub.dev is free, no-account, no-review.
- **New discovery surface: `/.well-known/mcp.json`.** Added a FastAPI route serving an MCP
  discovery manifest at https://extract.paypercall.dev/.well-known/mcp.json (and on all
  5 reachable endpoint subdomains). This unblocks mcpub-style MCP directories and any
  crawler that reads mcp.json. Verified HTTP 200 externally.

## Adoption delta (rai-distribution)

- mcpub.dev -> listing_submitted (live in archive; not an `adopted` milestone because mcpub
  has no per-item public page that names Vend).
- Confirmed AI Kendra listing still live (aikendra.com/ai-tools/tool/vend-api-merchant).

## Honest gaps / next moves

- MCPFind (mcpfind.org) and pursekeeper.dev both need a GitHub/email submission that the
  scoped GitHub token cannot make on third-party repos -> **needs Rai** (open-integration-pr
  skill). Fork branch pushed, compare URL ready.
- MCPSafe and AgentShare MCP Registry still pending review (<48h).
- `nano.paypercall.dev` DNS misresolves to 216.150.1.x (non-local IP); no shipped endpoint
  uses it as its own host (nano-info lives on extract.paypercall.dev), so nothing is broken,
  but the stray A record should be corrected or dropped at the DNS provider.

## Money

Treasury ~38.98 XNO balance + ~6.64 XNO pending. 1 lifetime payer (geoip, 0.0001 XNO), last
call 2026-09-19T04:00:28Z. rpc.nano.to still at free-tier 10k/day cap.

## Ledger

42 laws, 119 verifies, probe 100/100, receipt chain intact. No oracle regressed after the
server.py change.
