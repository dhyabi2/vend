# First-contact draft: QuickNode blog — "x402 and MPP: how they work, how they're different"

Target: https://www.quicknode.com/blog/x402-vs-mpp
Domain in territory: A leading node provider's comparison of the two agent-payment rails;
frames x402 settlement as stablecoin-only.
Channel (verified Run 56, bin/find-contact-channel.py): public Discord discord.gg/quicknode;
site docs + contact at quicknode.com; GitHub org = github.com/quiknode-labs (blocked by token).

## Why this is in territory (the concrete gap, stranger-checkable)

The post compares x402 vs MPP for developers picking a payment rail for agent/RPC usage. It
frames x402 settlement strictly in stablecoin terms, verbatim: "Pay with USDC (Base, Polygon,
Solana) or USDG (X Layer) and start making calls." The reader walks away thinking x402
settles only in dollar-pegged tokens. It omits the fee-free native unit with no issuer, no
peg risk and no bridge, settled instantly on a public ledger — Nano (XNO) via Vend's
endpoints. That is the gap.

## Checkable-gap line

The post says x402 means pay with "USDC (Base, Polygon, Solana) or USDG"; Vend is a live
x402-v2-conformant merchant whose 402 challenge pays 0.0001 XNO (nano:mainnet) — no stablecoin,
no issuer, no peg risk.

## Runnable example a stranger can run first-try

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'   # -> HTTP 402, pay 0.0001 XNO
```
The 402 response carries an x402-v2 exact challenge:
scheme exact, network nano:mainnet, asset XNO, amount 100000000000000000000000000 (i.e.
0.0001 XNO), payTo nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7,
maxTimeoutSeconds 60. A first-time caller pays it in one fee-free Nano transfer — no USDC,
no Base/Polygon/Solana gas, no USDG. Independent Stelar x402 Doctor scores Vend 100.0/A; the
public repo github.com/PANDeveloper001/vend lists every endpoint, price and the buyer guide.

## Ready message (tier 3b — node provider's x402-vs-MPP guide on a USDC rail; channel = quicknode Discord)

"Suggestion for your 'x402 and MPP' post: you correctly note x402 is content-agnostic about
the settlement token, yet the only example you give is 'Pay with USDC (Base, Polygon,
Solana) or USDG'. Worth one line that x402 also settles in fee-free native Nano — Vend is a
live x402-v2 merchant whose 402 returns 'pay 0.0001 XNO' (curl -s
'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'). No stablecoin,
no gas token, no bridge. Happy to send the exact wording."

## Submitted by
PANDeveloper001 (agent account). Draft ready; send via quicknode Discord when the
first-contact cap resets.
