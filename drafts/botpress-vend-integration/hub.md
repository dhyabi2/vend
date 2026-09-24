# hub.md

Integrate the Vend API Merchant into your Botpress bot: make your bot run
pay-per-call web extraction and web search, settled instantly in Nano (XNO)
via x402 — no API key, no signup.

## Actions

- **Extract Web Page** (0.0001 XNO): return clean text/markdown from any URL.
- **Web Search** (0.0001 XNO): return search titles, URLs and snippets via DuckDuckGo.

## Setup

1. Install the integration from the Botpress Hub (once published).
2. Optional: paste a settled payment's block hash into the `paymentHeader` config
   to reuse an existing balance window.
3. Call an action from your flow.

## How payment works

The endpoint answers HTTP 402 with an x402 challenge naming a `nano:mainnet` /
`XNO` destination and price. Send the exact amount to that address on-chain
(~1 second, zero fee), then retry with the block hash as `X-PAYMENT`.
