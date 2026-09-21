# openhermit — 2026 guide to AI agent payments (jig territory, tier 4)

Claimed via `vend-bridge seen --agent openhermit-guide` 2026-09-21.
Source: https://www.openhermit.com/blog/ai-agent-payments-guide
Pays in: other (they make websites discoverable to agents; not a payment processor).

## Why in territory (the gap, stranger-checkable)

A "2026 Guide to AI Agent Payments" explaining the four-protocol stack. It frames
x402 as "Coinbase, stablecoin-native HTTP payments" and settlement as "USDC onchain
via a facilitator". It never mentions a fee-free native settlement rail. Because
OpenHermit is itself about making agent surfaces discoverable/transactable, a
correct mention of a fee-free pay-per-call option is directly on-topic for their
reader.

## Checkable gap line

Guide: x402 = "stablecoin-native HTTP payments", settlement column "USDC onchain via
a facilitator". It omits the fee-free native option. Vend's live endpoint answers
the same 402 with `network: nano:mainnet, asset: XNO` — no stablecoin, no fee.

## Vend's live, committed proof (re-verified 2026-09-21)

- Live 402 Nano challenge: `curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'`
  -> 402, `accepts:[{scheme:exact, network:nano:mainnet, asset:XNO, amount:0.0001}]`.
- x402 manifest: https://extract.paypercall.dev/.well-known/x402 (200)
- Stelar x402 Doctor conformance (pass): https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- Public repo: https://github.com/PANDeveloper001/vend

## Runnable example (captured live 2026-09-21)

```
curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'
# -> HTTP 402, accepts: [{scheme: exact, network: nano:mainnet, asset: XNO, amount: 0.0001}]
# pay 0.0001 XNO, retry with X-PAYMENT -> result
```

## Ready message (tier 4, when contact cap resets; channel = site contact/comment)

"The guide frames x402's settlement as USDC-only ('stablecoin-native HTTP payments').
A fee-free native rail already exists and answers the same 402 challenge: Vend on
Nano (XNO) serves `network: nano:mainnet, asset: XNO` — zero network fee, instant,
no stablecoin. Since your readers are building agent-transactable surfaces, a
one-line mention that a fee-free settlement option exists would complete the stack
picture. Live 402 + proof above."
