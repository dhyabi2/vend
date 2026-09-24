# Calling a pay-per-call Nano x402 API from your agent code

A 3-minute tutorial. No signup, no API key, no monthly fee — pay Nano (XNO) per call,
settled on-chain in ~1 second.

## What you get

Vend ships 7 pay-per-call endpoints an AI agent can call directly:

| Endpoint | Price (XNO) | What it returns |
|----------|-------------|-----------------|
| `extract` | 0.0001 | Clean text/markdown from any URL |
| `check-link` | 0.0001 | HTTP status + redirect chain |
| `domain-info` | 0.0005 | DNS, WHOIS, TLS cert, headers |
| `web-search` | 0.0001 | DuckDuckGo web search |
| `geoip` | 0.0001 | IP geolocation |
| `nano-info` | 0.0005 | Nano account intelligence |
| `youtube-transcript` | 0.0005 | Captions from a YouTube URL |

Every endpoint speaks the open [x402](https://x402.org) protocol. The flow is the same
for every framework.

## The flow (2 HTTP round-trips)

1. **Call the endpoint** → you get back HTTP 402 with a payment challenge
   (price, pay-to address, `nano:mainnet` `XNO` accept).
2. **Send the Nano payment** → settles in ~1 second, returns a 64-char block hash.
3. **Retry with the block hash** in the `X-PAYMENT` header → HTTP 200 with your data.

## Plain Python

```python
import httpx, json

BASE = "https://extract.paypercall.dev"
CHALLENGE = None

# Step 1: probe -> read the 402 challenge
r = httpx.get(f"{BASE}/api/v1/extract", params={"url": "https://example.com"})
assert r.status_code == 402, r.text
c = r.json()
print("pay", c["price_xno"], "XNO to", c["pay_to"])

# Step 2 (wallet side, using feeless402):
#   from feeless402 import ... send c["pay_to"] c["price_xno"] XNO
#   -> returns block_hash

# Step 3: retry with the block hash
r2 = httpx.get(
    f"{BASE}/api/v1/extract",
    params={"url": "https://example.com"},
    headers={"X-PAYMENT": "<your-64-char-block-hash>"},
)
print(r2.json()["title"])   # "Example Domain"
```

## With vend-client (already handles steps 2–3)

```bash
# Install the vend-client wheel (served by Vend; NOT yet on PyPI, so do not use `pip install vend-client`)
pip install https://extract.paypercall.dev/static/packages/vend_client-0.1.0-py3-none-any.whl
vend-client extract --url https://example.com          # dry-run, shows price
vend-client --wallet /path/to/seed.txt extract --url https://example.com  # paid
```

## With the MCP endpoint

Vend is also a Model Context Protocol server at `https://extract.paypercall.dev/mcp`
(streamable HTTP, 7 tools). Any MCP client can surface the tools; each call returns the
x402 challenge that the client settles and retries.

## Why Nano

- **Instantly settled** — ~1 second, no bank rails.
- **Feeless** — the whole price is what the seller quotes; no gas, no platform cut.
- **Green** — Nano's ledger is a single tiny block-lattice, negligible energy.
- **Truly peer-to-peer** — no issuer that can freeze funds, no bridge, no off-chain batcher.

PyPay examples, more endpoints, and docs: https://extract.paypercall.dev/
Buyer's guide: https://extract.paypercall.dev/static/tutorial-call-x402-from-agent.md
