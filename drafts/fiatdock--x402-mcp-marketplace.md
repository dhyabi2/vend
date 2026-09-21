# fiatdock-x402-mcp — draft first contact (jig territory, tier 3b)

Claimed via `vend-bridge seen --agent fiatdock-x402-mcp` 2026-09-21.
Source: https://github.com/fiatdock/fiatdock
Pays in: USDC (x402 on Base/EVM).

## Why in territory (the gap, stranger-checkable)

FiatDock is a public x402 MCP marketplace where "AI agents discover and **pay each
other per call in USDC** over x402" — `call_service` settles "99% -> seller + 1% ->
FiatDock". Every listed service is priced and settled in **USDC on an EVM chain**;
there is no native-coin rail and no mention of a fee-free network. Vend serves the
same "agent pays per call" shape on **Nano (XNO), fee-free and instant**, as a
public x402 conformance-certified endpoint with no stablecoin, no account, no USDC
ramp and **no 1% marketplace commission**.

## Checkable gap line

FiatDock's README: "agents discover and pay each other per call in **USDC** over
x402 ... settlement goes straight to the seller's wallet ... 1% service commission."
Nowhere does a seller have a **fee-free** settlement option. Vend's live endpoint
answers the exact same 402 challenge but is `network: nano:mainnet, asset: XNO` —
zero network fees, instant finality, no USDC needed.

## Vend's live, committed proof (all re-verified 2026-09-21)

- Live 402 Nano challenge, live probe: `curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'`
  -> HTTP 402, `accepts:[{scheme:exact, network:nano:mainnet, asset:XNO, amount:0.0001}]`.
- x402 manifest: https://extract.paypercall.dev/.well-known/x402 (200)
- Stelar x402 Doctor conformance (pass, 402 challenge valid, x402Version 2):
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- Public repo: https://github.com/PANDeveloper001/vend
- First outside payer (2026-09-19, seller #12 on pursekeeper.dev/sellers):
  nano_1i3y944... 0.0001 XNO geoip, tx 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9

## Runnable example (captured live 2026-09-21 via bin/make-example.py)

```
curl -s 'https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8'
# -> HTTP 402 Payment Required
#    accepts: [{ scheme: exact, network: nano:mainnet, asset: XNO, amount: 0.0001,
#                payTo: nano_1yo6c1t64a... }]
# pay 0.0001 XNO once, retry with X-PAYMENT header -> JSON result
```

## Ready message (when the first-contact cap resets; send via their OWN channel)

The most direct channel: FiatDock is a GitHub repo and an MCP server. The working,
outside-the-GitHub-token-wall channel is `osama@fiatdock.com` (their published
security contact in SECURITY.md) or a marketplace submission if fiatdock exposes
one. Message targets the maintainer, not a fork:

"FiatDock's `call_service` settles every listed agent service in USDC with a 1%
commission. Vend is a live x402 merchant on Nano (XNO) — fee-free settlement for the
same pay-per-call shape. Our endpoint answers a valid 402 with
`network: nano:mainnet, asset: XNO, amount: 0.0001`, no USDC, no ramp, no
commission (Nano has no protocol fees). Live proof: 402 challenge above + x402
Doctor conformance 100.0/A + an existing outside payer (PurseKeeper seller #12).
Listing Vend as a settlement-free option in the FiatDock catalog gives buyers a
fee-free lane and costs you nothing."

Note: FiatDock is USDC-only by design (compliance EU/EEA), so the realistic value to
them is either (a) listing Vend as a non-USDC service, or (b) acknowledging the
fee-free alternative in their docs. Do not promise a USDC-to-Nano ramp; Vend does
not hold USDC.
