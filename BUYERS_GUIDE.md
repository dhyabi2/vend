# Vend Buyer's Guide

How to call any Vend endpoint and pay in Nano (XNO).

## Quick reference

| Step | What happens | Status code |
|------|-------------|-------------|
| 1. Call any endpoint | HTTP 402 with x402 payment challenge | 402 |
| 2. Send Nano to the challenge address | Payment settles in ~1 second | — |
| 3. Retry with the block hash | HTTP 200 with your data | 200 |

**Payment destination (all endpoints):** `nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7`


## Step-by-step

### Step 1: Probe an endpoint

```bash
curl -s https://extract.paypercall.dev/api/v1/extract?url=https://example.com
```

Response (HTTP 402):

```json
{
  "error": "payment_required",
  "message": "Pay 0.0001 XNO to nano_1yo6c1t64a... and retry with X-PAYMENT header",
  "price_xno": 0.0001,
  "pay_to": "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7",
  "accepts": [{
    "scheme": "exact",
    "network": "nano:mainnet",
    "asset": "XNO",
    "amount": "100000000000000000000000000",
    "payTo": "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7",
    "maxTimeoutSeconds": 60
  }]
}
```

### Step 2: Send the Nano payment

Send exactly `price_xno` XNO to `pay_to`. The `amount` field is in raw (10^30 raw = 1 XNO).

Use any Nano wallet — Nano Wallet (Nault), Natrium, a CLI wallet, or an exchange withdrawal.  
The payment settles in ~1 second and returns a 64-character block hash.

### Step 3: Retry with the block hash

```bash
curl -s -H "X-PAYMENT: <your-64-char-block-hash>" \
  https://extract.paypercall.dev/api/v1/extract?url=https://example.com
```

Response (HTTP 200):

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text": "This domain is for use in illustrative examples in documents...",
  "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples in documents...",
  "receipt": "..."
}
```

### Using feeeless402 (CLI)

```bash
# Install
pip install feeless402

# Send from a Nano wallet
nano-pay send \
  --to nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7 \
  --amount 0.0001 \
  --wallet "<your-seed-or-private-key>"
```

### Buying from another Vend endpoint

The flow is identical for every endpoint — only the subdomain and price change:

```bash
# Step 1: Probe (any endpoint)
curl -s https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8

# Step 2: Send 0.0001 XNO to nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7
# (or whatever price the endpoint quotes)

# Step 3: Retry with the block hash
curl -s -H "X-PAYMENT: <block-hash>" \
  https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8
```

## Full Python example

```python
import httpx, json

URLS = {
    "extract": "https://extract.paypercall.dev/api/v1/extract",
    "search": "https://search.paypercall.dev/api/v1/web-search",
    "domain": "https://domain.paypercall.dev/api/v1/domain-info",
    "check": "https://check.paypercall.dev/api/v1/check-link",
    "status": "https://extract.paypercall.dev/api/v1/status",
    "geoip": "https://geoip.paypercall.dev/api/v1/geoip",
    "nano-info": "https://extract.paypercall.dev/api/v1/nano-info",
    "youtube-transcript": "https://extract.paypercall.dev/api/v1/youtube-transcript",
}
PAY_TO = "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"

# Step 1: Get the 402 challenge
resp = httpx.get(URLS["search"] + "?q=nano+cryptocurrency")
assert resp.status_code == 402
challenge = resp.json()
price_xno = challenge["price_xno"]
print(f"Pay {price_xno} XNO to {PAY_TO[:20]}...")

# Step 2: Send the payment (use your wallet)
# The hash comes from your Nano wallet after sending
block_hash = input("Paste the block hash after sending: ")

# Step 3: Retry with payment proof
result = httpx.get(
    URLS["search"] + "?q=nano+cryptocurrency",
    headers={"X-PAYMENT": block_hash}
)
print(result.json()["results"][:3])
```

## Auto-buying with x402 SDK

If you have an x402-capable client (e.g. `@x402/fetch` for JavaScript, `feeless402` for Python), point it at any Vend endpoint URL and it handles the 402 negotiation automatically:

```js
import { wrapFetchWithPayment } from "@x402/fetch";

const paidFetch = wrapFetchWithPayment(fetch, client);
const res = await paidFetch(
  "https://search.paypercall.dev/api/v1/web-search?q=nano"
);
const data = await res.json();
console.log(data);
```

> **Note:** Most x402 SDKs default to USDC on Base. To pay in Nano, use an x402 client configured for `nano:mainnet`, or send the Nano payment directly and attach the block hash as `X-PAYMENT`.

## What you get

Each call returns structured JSON. Every response includes a receipt field for your records.  
Failed or duplicate payments are never charged — the endpoint returns 402 without processing.

## Pricing

| Endpoint | Price (XNO) | ~USD (at $4.50/XNO) |
|----------|-------------|---------------------|
| extract    | 0.0001 | $0.00045 |
| check-link | 0.0001 | $0.00045 |
| status     | 0.0001 | $0.00045 |
| web-search | 0.0001 | $0.00045 |
| geoip      | 0.0001 | $0.00045 |
| domain-info| 0.0005 | $0.00225 |
| nano-info  | 0.0005 | $0.00225 |
| youtube-transcript | 0.0005 | $0.00225 |

All settlement costs (Nano tx fee) = exactly 0 XNO.