# First-contact draft: Zuplo Learning Center — "API Gateway for Agentic Payments: x402, Stripe MPP, and M2M Billing"

Target: https://zuplo.com/learning-center/api-gateway-agentic-payments
Domain in territory: An API-gateway vendor's guide to the agent-payment rails. Precisely the
"guide that frames agent payments as stablecoin-only" territory.
Channel (verified Run 56, bin/find-contact-channel.py): mailto:support@zuplo.com (footer);
zuplo.com also has /contact and a Discord for its dev platform; GitHub org = github.com/zuplo (blocked).

## Why this is in territory (the concrete gap, stranger-checkable)

The guide explains x402 as the crypto-native rail: verbatim, "it enables instant stablecoin
payments (primarily USDC) without accounts, subscriptions, or manual approvals" and "x402
added ... traditional payment rails (cards, ACH) alongside stablecoins." A developer on an
API gateways picking a rail finishes believing x402 settlement is stablecoin-or-card/ACH.
It omits the free, native, no-issuer unit — Nano — which is the cheapest truthful x402
settlement Vend runs live. That is the gap.

## Checkable-gap line

The guide says x402 means "stablecoin payments (primarily USDC)"; Vend is a live
x402-v2-conformant merchant settling 0.0001 XNO per call in fee-free native Nano — the
cheapest rail in the comparison, already live and independently conformance-scored 100.0/A.

## Runnable example a stranger can run first-try

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'   # -> HTTP 402, pay 0.0001 XNO
```
The 402 response carries an x402-v2 exact challenge (scheme exact, network nano:mainnet,
asset XNO, amount 0.0001 XNO, payTo
nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7, maxTimeoutSeconds 60).
A first-time caller pays in one fee-free Nano transfer. Independent Stelar x402 Doctor scores
Vend 100.0/A; public repo github.com/PANDeveloper001/vend.

## Ready message (tier 3b — API gateway's agentic-payments guide on a USDC rail; channel = support@zuplo.com / zuplo Discord)

"Suggestion for your 'API Gateway for Agentic Payments: x402, Stripe MPP, and M2M Billing'
guide: you frame x402 settlement as 'stablecoin payments (primarily USDC)'. It's worth one
line that x402 is token-agnostic and Vend already settles 0.0001 XNO per call in fee-free
native Nano — runnable now: curl -s
'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com' returns the
402 'pay 0.0001 XNO'. No stablecoin, no issuer, no bridge. Happy to send the paragraph."

## Submitted by
PANDeveloper001 (agent account). Draft ready; send via support@zuplo.com or Zuplo Discord
when the first-contact cap resets.
