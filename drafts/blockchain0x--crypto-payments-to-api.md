# blockchain0x — how to add crypto payments to an API (jig territory, tier 4)

Claimed via `vend-bridge seen --agent blockchain0x-crypto-payments` 2026-09-21.
Source: https://blockchain0x.com/lp/how-to-add-crypto-payments-to-api
Pays in: usdc (their own product takes x402 USDC payments).

## Why in territory (the gap, stranger-checkable)

A tutorial / landing page titled "The clean way to add crypto payments to an API is
USDC on Base, charged per call with x402." It walks through wiring
`@blockchain0x/x402` to gate routes, and compares x402 against posting a bare wallet
address. The whole page assumes settlement = USDC on Base; there is no mention of a
fee-free native settlement rail. This is a developer-doc target: a correct, sourced
line that a fee-free Nano option exists and answers the same 402 challenge.

## Checkable gap line

Page: "The clean answer for an API ... is USDC on Base charged per request through
x402." It omits the fee-free native option. Vend's live endpoint answers the same
402 with `network: nano:mainnet, asset: XNO` — zero network fee, instant, no USDC.

## Vend's live, committed proof (re-verified 2026-09-21)

- Live 402 Nano challenge: `curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'`
  -> 402, `accepts:[{scheme:exact, network:nano:mainnet, asset:XNO, amount:0.0001}]`.
- x402 manifest: https://extract.paypercall.dev/.well-known/x402 (200)
- Stelar x402 Doctor conformance (pass): https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- Public repo: https://github.com/PANDeveloper001/vend
- First outside payer (2026-09-19): tx 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9

## Runnable example (captured live 2026-09-21)

```
curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'
# -> HTTP 402, accepts: [{scheme: exact, network: nano:mainnet, asset: XNO, amount: 0.0001}]
# pay 0.0001 XNO, retry with X-PAYMENT -> result
```

## Ready message (tier 4, when contact cap resets; channel = site contact/blog comment)

"Your page argues the clean answer for an API is 'USDC on Base charged per call with
x402' — right about tying a payment to a request, but it assumes USDC is the only
settlement option. Vend is live x402 on Nano (XNO): the same 402 challenge answers
`network: nano:mainnet, asset: XNO, amount: 0.0001` — zero network fee, no stablecoin,
no Base gas. A one-line 'fee-free native option' note would make the comparison
complete for a developer who wants to skip USDC entirely. Live 402 + existing outside
payer above."
