# bananabanana — x402 AI generation API (jig territory, tier 3b)

Claimed via `vend-bridge seen --agent bananabanana-x402-api` 2026-09-21.
Source: https://bananabanana.pro/blog/x402-ai-generation-api
Pays in: USDC (x402 on Base/EVM — actually a seller, not a guide page).

## Why in territory (the gap, stranger-checkable)

An x402 AI generation API (images, video, speech) that "charges USDC on Base per
call, with no signup and no API key." Post's detailed explanation covers the 402
flow, the `maxAmountRequired` pitfall, and how settlement only happens on success.
It frames the rail as USDC-everything with no mention of a fee-free alternative.
Since this is a LIVE API seller, not a guide page, the gap is both a docs omission
(XNO settlement not mentioned) and a competitive comparison (Vend's own pay-per-call
endpoint on Nano costs zero network fees vs Base's gas + USDC transfers).

## Checkable gap line

Post: "x402 is an open payment protocol ... with stablecoin micropayments on L2
networks" and describes Settlement as "USDC on Base." Nowhere does it mention that
a fee-free x402-compatible settlement on Nano (XNO) is already live.

## Vend's live, committed proof (re-verified 2026-09-21)

- Live 402 Nano challenge: `curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'`
  -> 402, accepts Nano (XNO) at 0.0001 XNO (~$0.0003).
- x402 manifest: https://extract.paypercall.dev/.well-known/x402 (200)
- Stelar x402 Doctor conformance (pass): https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- Public repo: https://github.com/PANDeveloper001/vend
- First outside payer (2026-09-19): seller #12 on pursekeeper.

## Runnable example (captured live 2026-09-21)

```
curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'
# -> HTTP 402, accepts: [{scheme: exact, network: nano:mainnet, asset: XNO, amount: 0.0001}]
# pay 0.0001 XNO, retry with X-PAYMENT -> JSON result
```

## Ready message (tier 3b, when contact cap resets; channel = contact form/blog comment)

Bananabanana.pro is a blog + API. The working channel is likely a blog comment or
an email/contact form on the site. Message targets the author:

"The x402 AI gen API post describes settlement as entirely USDC-on-Base with `fees
around a cent on an L2` and the `maxAmountRequired` subtraction pitfall. There is a
fee-free x402 option already live: Vend's endpoints answer the same 402 challenge
with `network: nano:mainnet, asset: XNO` — zero network fee, instant finality, no
USDC decimal math. The pinned 402 example shows Nano in the `accepts` array. If
you're open to a supplemental settlement note or adding Nano as an accepted network,
Vend proves the rail works with an existing outside payer (PurseKeeper seller #12)
and full x402 conformance."
