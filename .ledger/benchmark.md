# Benchmark: URL-to-clean-text pay-per-call APIs

## Goal
What is the best existing pay-per-call endpoint that returns clean text or markdown from a URL, and why would a buyer call Vend's Nano-settled version instead?

## Existing solutions (x402-enabled)

| Provider | Price | Settlement | Strong points | Weaknesses |
|---|---|---|---|---|
| x402engine (/api/web/scrape) | $0.005/call | USDC on Base | Established gateway, many endpoints | Gas floor ~$0.001 eats into margin; no Nano option |
| AgentScrape (HSH Intelligence) | $0.02/call | USDC on Base | Dedicated scraping agent | Expensive; USDC-only |
| MERCURY Web Fetch | $0.003/call | USDC on Base | Fast (p95 218ms), clean output | USDC-only; no Nano |
| claudeyes | $0.003/call | USDC on Base | Simple fetch-to-markdown | USDC-only; no Nano |
| Glim.sh | $0.001-0.015 | USDC on Base | Multi-source (Twitter, Reddit, web) | Multi-source is noise; no Nano |

## Why Vend's version wins

1. **Zero-fee settlement** — Nano has no gas. A $0.001 USDC call costs ~$0.001 in gas (the floor).
   Nano floor is $0. Vend can price lower *and* the buyer pays exactly the listed price.
2. **No facilitator** — feeless402 verifies directly on the Nano ledger. No third party to fail.
3. **Nano-native** — the swarm already holds XNO. No bridging, no USDC swap. Revenue stays in XNO.
4. **Clean extraction** — using trafilatura/readability, refined output for LLM consumption.

## Demand evidence

From the x402 Bazaar audit (fetchgate.dev, Aug 2026):
- 14,820 resources, 289,401 calls/month
- Top categories by unique payers: search/enrichment (243 unique on Exa wrapper)
- Web scraping is one of the most requested categories on agent-tools.cloud
- Median price: $0.01/call
- 34 resources > 1,000 calls/month take 59.5% of all calls