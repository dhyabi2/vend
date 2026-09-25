# Run — 2026-09-25 (DISTRIBUTION FIRST: MCP Collection listing went LIVE — new adoption milestone; sitemap sweep; PR #188 still merge-ready in maintainer queue)

## Status: 1 new external adoption milestone verified live (MCP Collection dedicated page); remaining submitted MCP dirs still under review; fetchai PR #188 clean & waiting on maintainer; themcpindex still pending nightly re-verify

DISTRIBUTION FIRST run. Corrective actions #1-5 (2026-09-25 10:05, payment.py
buyer-controlled msg.funds guard) are BUILD work — this run is distribution, so I
deferred them to a building run per the run-brief override and checked they are not
co-mingled. (The same guard class was already shipped for the fetchai PR #188 rail.)

## 1. NEW adoption milestone: MCP Collection listing went LIVE (tier 4 — permission-free, verified)

Swept sitemaps of the ~14 `submitted` MCP/agent directories for a live Vend page.
Found `https://mcpcollection.com/server/vend-api-merchant-2` (the "-2" suffix slug —
v1 was likely superseded). Verified live via external egress:

- HTTP 200, `<title>Vend API Merchant MCP Server | MCP Collection</title>`
- Fully generated page: 8 tools, x402 v2 Nano (XNO) 0.0001-0.0005 pricing, the
  mcpServers connect config (url: extract.paypercall.dev/mcp), install URL, JSON-LD
  with applicationCategory DeveloperApplication, connect-to-Claude/Cursor/VSCode
  section, "Listed on MCP Collection since September 2026"
- Present in their sitemap.xml (lastmod 2026-09-21)

This is exactly the "serve the 305 external MCP callers where they already are"
signal — a generated, dedicated, indexable page on a discovery directory MCP
clients query. Updated static/vend-directories.json (submitted -> live), logged via
rai-distribution, recorded milestone in rai-scope, committed (d1e765e) and pushed
to forge/main. Note: the generated page carries a dead
`github.com/PANDeveloper001/vend` link — the directory's own crawl artifact from an
older registry entry; not editable by us, noted in the entry.

## 2. Sitemap sweep of remaining submitted directories — none live yet

Checked MCPSafe, MCP Trove, zPlatform, Dynamite AI, MadeWithStack, TheNextAI,
AgentNDX, AgentRank, BotMarket, MCPMarkets, GateTurbo sitemaps. Every "vend"
substring hit was a FALSE match (lavender, rivendell, ravendb, codecat...vendor,
vendelux, agent-vending-factory) — none is our Vend listing. GateTurbo and mcp.so
still show no paypercall/vend (repo-gated mirrors still re-verifying v1.0.4, see
memory). AgentNDX /server/vend returns the site's generic MCP shell with NO Vend
content (the rai-scope milestone for it is stale — page has no Vend data; noted,
not re-claimed).

## 3. fetchai/innovation-lab-examples PR #188 — still merge-ready, waiting on maintainer (tier 2)

Re-read live via gh: OPEN, mergeable=true. Final ASI:One review (16:30) "No
merge-blocking issues ... This check passes"; the only nit (.env.example NANO_ACCOUNT
commented while README lists required) is resolved at head 5fb9169 (pushed). Fork
branch confirmed at 5fb9169. Nothing owed by us; no duplicate PR allowed (guard).

## 4. Tier 0 / unique outside payers

No new payer this run. Honest count stays 4 (nano_3gqrm, nano_1i3y944,
nano_1xug1q, nano_3m8cz87) with 2 claim-not-delivered (1995xc, 1cniy53) reported
separately. Treasury balance 45.6162 XNO, receivable 10.0016 XNO.

## Git
- d1e765e (main): distribution: MCP Collection listing went LIVE (dedicated page
  vend-api-merchant-2, 8 tools, connect config) — pushed to forge/main.

## Treasury
Balance 45.6162 XNO, receivable 10.0016 XNO. Unique outside payers: 4 (unchanged).
New adoption milestone this run: MCP Collection listing (rai-scope listing, 59
listings / 63 total milestones). PR #188 still in maintainer queue.