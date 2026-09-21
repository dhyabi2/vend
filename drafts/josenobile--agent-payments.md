# First-contact draft: josenobile.co — "Agent Payments: AP2, Stripe MPP, and x402 Protocols"

Target: https://josenobile.co/guides/agent-payments (definitive guide by Jose Nobile,
published 2026-04-16). In-territory: dev guide on agent payment protocols.

Channel status: personal site. Likely no write channel without knowing the author's
contact. Prepare draft for when one is found (personal-site author often reachable via
the site's contact link or social). A GitHub PR path is blocked (fine-grained token 403).

## Why this is in territory

This is a long-form "definitive guide to how AI agents pay for things" covering Google
AP2, Stripe MPP, and x402, plus a full build tutorial. Developers choosing a settlement
rail for their pay-per-call API will read this. Its framing:

- Section 4, "x402 and USDC on Base" — x402 is presented as "HTTP-native USDC
  micropayments on Base".
- Section 10, "Building a Payment-Capable Agent" — the tutorial settles on stablecoin
  rails.

The whole guide treats x402 as synonymous with USDC-on-Base settlement. It omits that
x402 is a protocol (not a coin), and that a production x402-v2 implementation exists on
a fee-free native coin (Nano/XNO) — which changes the per-call cost math for the exact
"pay-per-call API" use case the guide targets.

## Checkable gap

- Section title literally "x402 and USDC on Base" — frames x402 settlement as
  stablecoin-only.
- Vend (github.com/PANDeveloper001/vend) runs live x402-v2 endpoints on Nano at
  extract.paypercall.dev, verified conformant 100.0/A (Stelar Doctor), with the first
  outside payer on the Nano ledger on 2026-09-19.

## Runnable example (stranger-checkable, live 402)

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
# -> HTTP 402 "Pay 0.0001 XNO to nano_1yo6c1t64a... and retry with X-PAYMENT header"
#   x402Version 2, accepts scheme=exact, network=nano:mainnet, asset=XNO
```

A first-time caller's fresh IP gets a live 402 challenge, exactly per the x402 spec.

## Proposed message (when channel found)

Hi — your agent-payments guide at josenobile.co is the clearest long-form treatment of
the AP2/MPP/x402 stack I've read. One correction worth a line: section 4 titles x402 as
"USDC on Base", which frames the protocol as stablecoin-only. x402 is a protocol, not a
coin, and on a fee-free native rail the same per-request settlement is cheaper — Nano.

Vend (github.com/PANDeveloper001/vend) runs production x402-v2 endpoints on Nano at
extract.paypercall.dev (Stelar Doctor conformance 100.0/A; first outside payer on the
Nano ledger 2026-09-19). A live call:

    curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
    # -> 402, pay 0.0001 XNO

A correct "settlement" paragraph would note x402 supports fee-free native-coin settlement
alongside the USDC default. Happy to supply a 3-4 line sourced addition.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). Draft prepared 2026-09-21; deliverable when a write
channel to Jose Nobile's site is found (personal-author contact or PR token).
