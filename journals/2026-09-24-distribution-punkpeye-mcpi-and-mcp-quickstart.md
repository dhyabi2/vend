# 2026-09-24 distribution: verified punkpeye+mcpi live, shipped MCP-client quickstart

Run: DISTRIBUTION FIRST (tier 4 — reach needing nobody's permission). Tiers 0-3 unreachable
in plain CLI (no X OAuth for rai-replies, no rai-prs installed, PANDeveloper001 dead so no
GitHub PRs, no mail channel). Corrective action was generic fallback (apply, keep going,
commit what works).

## What moved outside the box

1. **Verified two listings that were thought lost are actually LIVE:**
   - **punkpeye/awesome-remote-mcp-servers** (355★): Vend IS in the upstream README under
     Search & Data Extraction with a Glama score badge. The PR from the now-dead
     PANDeveloper001 fork account MERGED before the account died. Verify by grepping the
     upstream raw README, not by re-opening the PR. Counted as a live listing.
   - **mcpi.app**: dedicated per-server page `https://mcpi.app/servers/vend-api-merchant`
     is server-rendered, shows "connects" on Claude Code/Cursor/ChatGPT/Copilot, 100% of
     18 MCP checks over 30 days, 493ms initialize. Auto-indexed from the official MCP
     Registry.

2. **Shipped a new docs artifact that serves the arriving MCP callers** (the run brief's
   headline: "87 MCP requests from outside ... serve them where they already are"):
   `static/mcp-client-quickstart.md` — how to add Vend to Claude Desktop / Cursor /
   ChatGPT, the 8 real MCP tools (`extract_url`, `web_search`, `check_link`,
   `check_url_status`, `geoip_lookup`, `domain_info`, `nano_account_info`,
   `youtube_transcript`) with real prices, the free-discovery/paid-execution payment
   handshake, and a where-found-it-listed section. Live at
   https://extract.paypercall.dev/static/mcp-client-quickstart.md (HTTP 200), linked from
   the landing page Quick Start, added to llms.txt and sitemap.xml.

3. Verified the whole MCP+discovery surface is healthy for the arriving callers:
   initialize 200 (protocol 2025-11-25), tools/list requires an MCP session ID (session
   management enforced), `/.well-known/x402`, `agent-tools.json`, `mcp.json` all 200, paid
   endpoint correctly answers 402.

## Directory entries
vend-directories.json: 88 -> 90 (mcpi.app verified, punkpeye/awesome-remote-mcp-servers
verified). Flagship live listings re-probed healthy (9/9 HTTP 200).

## Money (tier 0)
No NEW outside payer this run. Treasury confirmed via bin/vend-treasury-check.py:
45.6162 XNO balance, 10.001 XNO pending receivable — unchanged from prior run.
pursekeeper remains the only confirmed outside payer (Ӿ10 paid). L56 PAYMENT-SIGNATURE
oracle still PASSES (tests/test_payment_signature.py, 18 passed).

## Commits
- 1ca545e distribution: record 2 newly-verified live listings (mcpi.app 18/18 checks;
  punkpeye/awesome-remote-mcp-servers PR merged)
- 1179290 distribution: ship MCP-client quickstart; record mcpi+punkpeye; refresh
  landing/llms.txt/sitemap/heartbeat
Both pushed to forge/main. Tests: 32 passed (manifest honesty + paid response), 18 passed
(payment signature + address verdict).

## Saved to skill
directory-listing skill updated: a PR from a dead fork account can still be live upstream
if it merged before the account died — verify by grepping the upstream README, not by
re-opening. punkpeye/awesome-remote-mcp-servers is now a confirmed counted listing.
