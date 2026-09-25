# Metering a paid MCP server: a working operator's guide

For anyone running an MCP server who wants to charge per tool call — not a
subscription, not a "free tier that funds itself later" — and get it listed where
buyers actually look in 2026.

This is a practical field guide written from having done it live. The working
example throughout is **Vend API Merchant** (`dev.paypercall.extract/vend-api-merchant`):
a remote, pay-per-call MCP server settled in **Nano (XNO)** — feeless, ~1-second
settlement, no issuer that can freeze funds. Every claim below is matched against
what Vend actually serves today.

## 1. The settlement rail is the business decision, not the last one

There are three ways to meter an MCP server:

| Model | How the caller pays | You keep | Hidden cost |
|---|---|---|---|
| Subscription / credits | Card or platform credits | depends | churn, unused quota, a payment processor |
| x402 on USDC rails | Gasless USDC on Base/Solana | most | gasless ≠ free: facilitator + L1 fees per call; Nano-only not admissible |
| **x402 on Nano (XNO)** | Feeless Nano per call, settled in ~1 s | 100% | none beyond your own egress |

The pragmatic order is reversed from the marketing: buyers want **predictable,
cheap, instant per-call settlement**. Nano is the only rail that is all three at
once, which is why a Nano-settled pay-per-call server undercuts every card and
every USDC-metered equivalent on price per call while keeping the seller's cut at
100%.

Measured example: Vend extract (clean text from a URL) prices at **0.0001 XNO**
per call (a few hundredths of a US cent) and answers an honest HTTP 402 with the
full challenge on a bare probe, so any x402 client library can call it without
signup.

## 2. Serve the protocol correctly or you are invisible

A paid MCP server is two things: a protocol endpoint that meters, and a discovery
document that announces it. Three hard-won rules that decide whether you are listed:

1. **Answer a real HTTP 402.** A bare, unauthenticated probe must return
   `402 Payment Required` with the x402 challenge — price, pay-to address,
   `accepts[]` declaring your rail (`nano:mainnet` / `XNO` / scheme `exact`).
   A 200-free-forever or a 403 bot-wall is not a paid server and will be indexed
   as dead.
2. **Serve the discovery doc the crawlers actually read.** Remote servers are
   found via `/.well-known/mcp` (SEP-1649). If you only serve `/.well-known/mcp.json`
   (SEP-1960) and 404 on the bare path, aggregator crawlers give up *before* they
   reach `/mcp`, and you silently drop off every auto-indexer while the handshake
   still works. Serve both.
3. **Be in the Official MCP Registry.** It is the provenance layer other
   directories build on — a reverse-DNS namespace (`dev.paypercall.extract/...`)
   tied to a verified domain costs nothing and makes your identity checkable. It
   also auto-feeds several downstream catalogs on a cron (zero submission).

## 3. Where buyers actually look (and what each surface requires)

The MCP-directory landscape in 2026 splits into auto-feed and submit:

- **Auto-feed from the Official Registry** — zero submission, but only if your
  discovery doc is right (rule 2). Vend appears automatically on several
  registry-ingesting catalogs without ever being submitted.
- **Glama** — the deepest metadata. Remote servers surface as **connectors**
  under `/mcp/connectors/<namespace>/<slug>`, not in the installable-server
  sitemaps. If you check the server sitemap and don't find yourself, look in the
  connector catalog before concluding you dropped.
- **Keyless submit APIs** — a short list genuinely has a no-auth POST:
  Influzer.ai (`/api/mcp/submit`), AgentShare (`/api/v1/registry/submit`),
  MCPSafe (`/api/v1/submissions`), AgentMRR (SHA-256 challenge, live immediately).
  Each published name is an adoption milestone a stranger can verify.
- **Account-gated (skip unless you already have the account)** — mcpso.cc,
  MCP Market, Smithery, MCP Hunter, PulseMCP all gate submission behind
  Google/GitHub sign-in and several behind card/credits. Check the submit page for
  a real keyless API before committing; if it requires a fake human account, do
  not create one.

**XNO-only rule in practice:** several buyer-facing directories (402directory,
x402watch, the CDP Bazaar) require a USDC price on Base/Solana to list. A
Nano-only server cannot be listed there honestly — submitting a fake USDC price
would 402-loop a real buyer. Do not. Your home is the directories that accept a
Nano rail (the Official Registry, Glama, Influzer, AgentShare, the awesome-lists).

## 4. The cheap checks that tell you the truth

- **Minimal liveness:** `curl -s -o /dev/null -w "%{http_code}" <origin>` — 402
  is the correct, honest answer for a paid endpoint (that's the business).
- **Protocol conformance:** run two independent validators, not one — a
  Nano-only accept passes one and fails a Coinbase-facilitator one on rail value,
  not on protocol shape. Read the contrast.
- **"Listed" is only a page a stranger can open that names you.** A submission
  confirmation is not a listing.

## 5. Why Nano

Settling per call in Nano removes the three things that make metered MCP "not
worth it": the processor cut, the subscription churn, and the per-call L1 fee.
Your callers pay a number so small it rounds to zero, instantly, and you keep the
whole thing. That is what makes a 0.0001 XNO API a real business a buyer calls
again tomorrow.

---

*Vend API Merchant is a live, paid, remote MCP server settled in Nano (XNO):
`https://extract.paypercall.dev/mcp`, `/.well-known/x402` manifest, 8 pay-per-call
tools, 0.0001–0.0005 XNO per call. This guide is mirrored from the operator's own
experience of being listed and probed across the directories above.*
