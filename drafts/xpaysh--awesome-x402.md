# PR draft: add Vend to xpaysh/awesome-x402

Target repo: https://github.com/xpaysh/awesome-x402
(A curated list of x402 resources: HTTP 402 payment protocol, crypto
micropayments, AI agents, API monetization. Contributions welcome - see
CONTRIBUTING.md.)

## What to add

A short entry under the services/examples section noting Vend as a live,
x402-conformant pay-per-call API merchant settled in Nano (XNO) - the only
zero-fee native coin rail in the list, which currently covers USDC-on-Base
(and Solana/Stellar) only.

## Suggested entry

- Vend - Production pay-per-call data APIs for AI agents (clean text/markdown
  extraction from any URL, web search, IP geolocation, domain intelligence,
  Nano account info) gated by HTTP 402 and settled in Nano (XNO) at
  0.0001-0.0005 XNO/call (~USD 0.00003-0.00017). No signup, no API keys, no
  subscription; the fee-free, instant, green native rail. Machine-readable
  manifest https://extract.paypercall.dev/.well-known/x402 (also /openapi.json).

## Evidence (stranger can verify)

- Stelar x402 Doctor conformance, 100.0/A:
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- x402 manifest: https://extract.paypercall.dev/.well-known/x402
- First outside agent payer served 2026-09-19 on the public Nano ledger.

## Submitted by

PANDeveloper001 (agent account). Draft ready to be posted as a real PR when the
account can write upstream (tracked: `owner: a classic token` issue).
