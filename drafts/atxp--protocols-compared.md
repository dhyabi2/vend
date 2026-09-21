# First-contact draft: ATXP — "Every Agent Payment Protocol Compared: X402, ACP, UCP, AP2"

Target: https://atxp.ai/blog/agent-payment-protocols-compared/ (published 2026, updated
March 8 2026; ATXP = Circuit & Chisel's agent identity+payments+email+tools product).
In-territory: a detailed developer-facing comparison of agent payment protocols.

Channel status: ATXP is an active product with its own site (atxp.ai) and a `npx atxp`
CLI. A real company — likely reachable via a contact page / Discord / GitHub org. A GitHub
PR to their repo is blocked by the fine-grained token (403). Prepare draft for their own
channel (contact / support), or the token day.

## Why this is in territory — it states x402's weakness Vend directly solves

This comparison is unusually valuable because it names x402's real friction and Vend
answers it. On Coinbase X402, the article says:

> "The crypto dependency — USDC on Base — is also a real friction point for developers
> who aren't building in the Web3 ecosystem."

And its comparison table lists X402's footprint as "Yes (USDC on Base)". The author's
whole framing is that x402 = crypto = USDC-on-Base. It omits the production x402
implementation on a fee-free native coin (Nano/XNO) where settlement has no gas and no
USDC on-ramp — exactly the "friction point" the article flags for non-Web3 developers.

## Checkable gap

- Comparison table: X402 "Crypto Required: Yes (USDC on Base)"; prose calls the USDC-on-Base
  dependency "a real friction point".
- Vend (github.com/PANDeveloper001/vend) runs live x402-v2 endpoints on Nano at
  extract.paypercall.dev (conformance 100.0/A, Stelar Doctor), first outside payer on the
  Nano ledger 2026-09-19.

## Runnable example (stranger-checkable, live 402)

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
# -> HTTP 402 "Pay 0.0001 XNO to nano_1yo6c1t64a... and retry with X-PAYMENT header"
#   x402Version 2, scheme=exact, network=nano:mainnet, asset=XNO — no gas, no USDC
```

A first-time caller's fresh IP gets a live 402 challenge per spec.

## Proposed message (when channel found)

Hi — your "Every Agent Payment Protocol Compared" post is one of the few that names x402's
real weakness: the section on Coinbase X402 calls "the crypto dependency — USDC on Base — a
real friction point for developers who aren't building in the Web3 ecosystem." That's the
gap a fee-free native rail closes. x402 is a protocol, not a coin, and it already runs on
Nano.

Vend (github.com/PANDeveloper001/vend) serves production x402-v2 endpoints on Nano at
extract.paypercall.dev (Stelar Doctor conformance 100.0/A, first outside payer 2026-09-19):

    curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
    # -> 402, pay 0.0001 XNO — no gas, no USDC, no on-ramp

A one-line note in the X402 row ("also settles fee-free on native coins, e.g. Nano")
would correct the "USDC on Base" framing and answer the friction point you raised. Happy
to supply the sourced line.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). Draft prepared 2026-09-21; deliverable when an ATXP
contact/write channel becomes usable.