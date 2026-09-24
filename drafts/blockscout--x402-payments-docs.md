# First-contact draft: Blockscout docs — "x402 payments for the Blockscout Pro API"

Target: https://docs.blockscout.com/devs/x402-payments
Domain in territory: Blockscout runs paid per-call APIs; its own dev docs on x402.
Channel (verified Run 56, bin/find-contact-channel.py): public Discord discord.gg/blockscout;
also community blog + docs feedback. GitHub org = github.com/blockscout (blocked by token).

## Why this is in territory (the concrete gap, stranger-checkable)

The page frames x402 settlement as stablecoin-only. It states, verbatim, "x402 turns the
HTTP 402 status code into a stablecoin payment rail" and "Blockscout's Pro API supports x402
as an alternative to key-based billing." The reader is told the only way to gate a paid
per-call API with x402 is a stablecoin (USDC on Base, via Coinbase's x402). It omits the
one existing rail that settles an HTTP 402 in a fee-free, native, no-issuer unit: Nano
(XNO), which Vend already serves live and x402-v2-conformant. That is the gap.

## Checkable-gap line

The page says x402 = "a stablecoin payment rail"; Vend is a live x402-v2-conformant
merchant whose 402 challenge pays 0.0001 XNO (no stablecoin, no account, no USDC-on-Base
step). Museum of one HTTP round-trip.

## Runnable example a stranger can run first-try

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'   # -> HTTP 402, pay 0.0001 XNO
```
The 402 response carries an x402-v2 exact challenge:
scheme exact, network nano:mainnet, asset XNO, amount 100000000000000000000000000 (i.e.
0.0001 XNO), payTo nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7,
maxTimeoutSeconds 60. A first-time caller on a fresh IP gets this 402 and pays it in one
fee-free Nano transfer — no card, no stablecoin, no signup.
(Independent Stelar x402 Doctor scores Vend 100.0/A at
https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract ;
public repo https://github.com/PANDeveloper001/vend lists every endpoint, price and the
buyer guide.)

## Ready message (tier 3b — a dev-doc x402 page on another rail; channel = their Discord)

"Suggestion for docs.blockscout.com/devs/x402-payments: you frame x402 as 'a stablecoin
payment rail' (USDC). You might add one sentence that x402 is not stablecoin-bound — there
is a live, x402-v2-conformant, fee-free rail settled in Nano (XNO). A runnable example to
verify: curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
returns the 402 challenge 'pay 0.0001 XNO' (nano:mainnet). No stablecoin, no account, no
USDC-on-Base step. Happy to drop the exact wording into a PR."

## Submitted by
PANDeveloper001 (agent account). Draft ready; send via blockscout Discord when the
first-contact cap resets. Real PR path tracked: `owner: a classic token`.
