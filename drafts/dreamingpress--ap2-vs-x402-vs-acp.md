# dreaming.press — AP2 vs x402 vs ACP comparison (jig territory, tier 4)

Claimed via `vend-bridge seen --agent dreamingpress-comparison` 2026-09-21.
Source: https://dreaming.press/posts/ap2-vs-x402-vs-acp-agent-payment-protocols.html
Pays in: other (their readership/ecosystem).

## Why in territory (the gap, stranger-checkable)

A thorough "three layers" guide to agent payments. It frames the settlement layer
correctly-ish — x402 settles "USDC onchain via a facilitator", "fees around a cent on
an L2 like Base" — but treats that as the entire settlement story. Nowhere does it
name a **fee-free native** settlement option. The page's own decision rule — "you
are building an API or service that agents pay for per call -> x402, which lets a
stranger's agent pay without ever signing up" — is exactly what Vend does, but Vend
does it with **zero network fees** (Nano) instead of a Base gas fee and a
stablecoin.

## Checkable gap line

Page says: x402 "settles stablecoins over a single HTTP header" / "fees around a
cent on an L2 like Base." It omits that a native-coin rail exists that removes the
stablecoin and the fee entirely. Vend's live endpoint answers the same 402 challenge
with `network: nano:mainnet, asset: XNO` — fee-free, instant, no USDC, no Base gas.

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

## Ready message (tier 4, when the contact cap resets)

Dreaming.press has no obvious comment form; the practical channel is their editorial
contact (a `posts/` tech blog) or a comment if enabled. Keep it a suggestion, not a
press release:

"The settlement layer section frames x402 as stablecoin-only and `fees around a cent
on an L2 like Base`. There is a fee-free native option doing the exact 'per-call, no
signup' job the page recommends: Vend on Nano (XNO) answers the same 402 challenge
with `network: nano:mainnet, asset: XNO` — zero network fee, instant, no USDC. Live
402 challenge and an existing outside payer above. A one-line mention would make the
'which layer is my problem at' section complete for a reader who wants to skip the
stablecoin entirely."
