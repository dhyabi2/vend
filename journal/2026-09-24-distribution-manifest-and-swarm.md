# 2026-09-24 distribution run — manifest honesty + new-directory sweep

## What this run did
DISTRIBUTION FIRST run. Tiers 1-2 unreachable (no X OAuth for rai-replies,
rai-prs not installed). Focus: serve the 910 inbound MCP callers by keeping
the discovery surface honest, and sweep for genuinely new keyless listing
surfaces.

## Fixed the served x402 manifest (distribution-quality defect)
The live `/.well-known/x402` carried ONE resource with `accepts: []` — the
free `/api/v1/delivery-proof` attestation endpoint — which violates the
manifest-honesty rule: a generic x402 client cannot learn what such a resource
wants (the same defect the outside auditor Nuwa flagged for balance). Fix:
- Moved delivery-proof OUT of `resources` into a new top-level `free` block
  with `documented_under: docs` (it is a free attestation endpoint, not a
  payable resource; x402dash correctly refuses to force-register it).
- Added a top-level `trial` block: `{"limit":5,"window":"1 day","scope":"per-IP"}`
  so a budgeting client can compute the real price instead of the metered one.
- Extended `test_manifest_honesty.py` from 4 to 6 tests (no empty accepts,
  balance not in resources, trial declared, free/documented not payable
  resources, paid resources carry nano payTo).
Verified live after `systemctl restart vend-api`:
  23 resources / 0 empty accepts / trial + free blocks present,
  69 tests pass, paid endpoints still answer 402, /health and MCP initialize
  return 200. Committed 08a44a1 and pushed to forge/main (scan-clean).

## New-directory sweep (logged docs, none keyless-viable for a Nano x402 host)
- WebMCP Directory: keyless but WebMCP = browser-side modelContext/registerTool
  in-page; Vend is a server-side remote MCP endpoint -> scan finds nothing. docs.
- Apify x402 directory (yadroo/x402-endpoints): analytics Actor over Coinbase
  CDP Bazaar (USDC only); not a submission surface. docs.
- MCPMarkets: free but REQUIRES a public GitHub URL (same structural gate as
  MCP.Directory; PANDeveloper001 dead 404). docs.
- wmcp.sh retry: still HTTP 500 "Submit failed" server-side. Already logged.
- Re-probed 6 pending MCP directories: all html 200 but human review still not
  complete (AgenticSkills, GateTurbo, MadeWithStack, mcpservers.org,
  MCP Agents Market, MCP Collection). AgenticSkills + GateTurbo (~48/72h
  review) still show NO Vend card — do not re-submit; re-check next run.

## Money (tier 0)
Unique outside payers still 1 (pursekeeper, Ӿ10 paid, receivable Ӿ10.001).
No new paid calls this run; no new unique outside payer. Reported honestly.

## Blockers (unchanged)
- Keyless distribution is nearly saturated; the highest-value open item —
  closing "stock exact settles" with a pursekeeper PAYMENT-SIGNATURE re-probe —
  needs a writable channel (X/GitHub/email) this plain-CLI box lacks. Must go
  through Rai/owner.
- GateTurbo Grade-A slot is explicitly open (Nano-settled competitor absent) but
  needs the human review to complete; re-verify next run.

## Next run
- Verify AgenticSkills + GateTurbo live pages (reviews due ~09-25/26); promote
  to rai-scope adopted only when a page that names Vend loads signed out.
- Ask Rai/owner for a writable channel to close the pursekeeper re-probe.
