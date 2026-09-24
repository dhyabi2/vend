# Vend API Merchant — Botpress integration (draft)

Lets a Botpress bot call Vend pay-per-call endpoints (extract, web-search) settled
in Nano (XNO) via x402 v2. No API key, no signup — the wallet is the account.

## Actions

| Action | Endpoint | Price (XNO) | What it does |
|--------|----------|-------------|--------------|
| `extract` | `https://extract.paypercall.dev/api/v1/extract?url=` | 0.0001 | Clean text/markdown from any web page |
| `webSearch` | `https://search.paypercall.dev/api/v1/web-search?q=` | 0.0001 | Web search via DuckDuckGo |

## Payment flow

1. Action calls the endpoint -> HTTP 402 with an x402 challenge
   (`accepts: [{scheme:"exact", network:"nano:mainnet", asset:"XNO", payTo:"nano_1yo6c1t6...", amount:"<raw>"}], price_xno: 0.0001`).
2. Send `price_xno` XNO to `pay_to` on-chain (~1 s, zero fee).
3. Set the integration config `paymentHeader` to the 64-char block hash and retry
   -> HTTP 200 with the JSON result.

## Verified against the live endpoint (2026-09-20)

- `GET /api/v1/extract?url=https://example.com` -> HTTP 402, `price_xno: 0.0001`,
  `accepts[0].network: nano:mainnet`, `asset: XNO`.
- `GET /api/v1/web-search?q=nano+cryptocurrency` -> HTTP 402.

## Status

DRAFT only. Not built with the Botpress CLI (`bp init --type integration`), not
verified against the current SDK types, and not deployed to the Botpress Hub.
Integration `definition` here matches the Botpress SDK shape but must be regenerated
with `bp` and tested before use or submission.

## Source / docs

- Backend: https://github.com/PANDeveloper001/vend
- Docs: https://extract.paypercall.dev/ , https://extract.paypercall.dev/openapi.json
