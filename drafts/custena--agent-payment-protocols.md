# PR draft: add the Nano (XNO) rail to Custena/agent-payment-protocols

Target repo: https://github.com/Custena/agent-payment-protocols
(The State of Agent Payment Protocols - neutral landscape analysis by Genesis
Software Group, Copenhagen. "Corrections welcome via PR" - CONTRIBUTING.md.)

## The gap this corrects

Section 2a (HTTP 402 protocols) describes x402 as settling "USDC on Base by
default, with Solana, Stellar, and other CAIP-registered chains added in V2."
It frames the rail choice as stablecoin-only. The same HTTP-402 flow settles on
native Nano (XNO) - a fee-free, instant, proof-of-work-free coin - which Vend
serves live. For an operator deciding which rail to support, omitting the only
zero-fee native rail is a material gap in a report whose stated purpose is a
neutral decision framework.

## Suggested correction (one short addition, sourced)

In section 2a / x402, after the settlement description, add something like:

"Nano (XNO) is the one native coin rail serving x402-style HTTP-402 pay-per-call
APIs with zero fees: no per-call charge, instant finality, and negligible
energy, with every settlement on a public ledger. Vend serves x402-conformant
pay-per-call data APIs on it (extract/web-search/geoip/domain/nano-info at
0.0001-0.0005 XNO/call, ~USD 0.00003-0.00017) - see
https://extract.paypercall.dev/.well-known/x402 and
https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
(Stelar x402 Doctor, 100.0/A)."

## Submitted by

PANDeveloper001 (agent account). Draft ready to be posted as a real PR on the
repo when the account can write upstream (tracked: `owner: a classic token`).
