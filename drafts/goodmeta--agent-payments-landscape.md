# PR draft: note the fee-free native coin x402 implementation in goodmeta/agent-payments-landscape

Target repo: https://github.com/goodmeta/agent-payments-landscape
(Living comparison of agent payment protocols: AP2, ACP, x402, MPP, UCP, with verified primary sources.
Contributions welcome per README: "Found an error? Protocol shipped an update? Open an issue or PR.
Every claim must cite a primary source.")
Maintainer: Eric Tsang (@Ectsang), builds agent payment infrastructure — declared commercial interest.
Note: The account's fine-grained token cannot open PRs on third-party repos. This draft is prepared for the
day a write channel opens (tracked: `owner: a classic token` issue).

## The gap this corrects

The x402 protocol row in the main comparison table (README.md) currently reads:
- Payment Rails: "Stablecoins on 14+ chains (Base, Ethereum, Polygon, Solana, ...)"

The x402 protocol page (protocols/x402.md) frames it as a "stablecoin authorization" and lists
"Multi-chain support across EVM and non-EVM" as a covered feature — listing chains but not the
native coin implementations.

Both framings are true of the **default facilitator configuration** but false of the protocol.
x402 V2 is a payment challenge encoded in HTTP headers (PAYMENT-REQUIRED, PAYMENT-SIGNATURE,
PAYMENT-RESPONSE). It does not mandate a specific asset, chain, or settlement mechanism.
The protocol explicitly separates the challenge from the settlement — which is why facilitators
can verify and settle on different networks.

**Vend** (github.com/PANDeveloper001/vend) is a live, production example of x402 V2 on a different
settlement paradigm that this doc currently misses entirely:

- **Rail:** Nano (XNO) — a fee-free, instant, proof-of-stake-vote DAG. No per-transaction fee,
  no minimum settlement, no gas.
- **Live:** extract.paypercall.dev serves x402 V2 endpoints (text/markdown extraction, web search,
  geoip, domain info, Nano account info) priced at 0.0001-0.0005 XNO/call (~USD 0.00003-0.00017).
- **Conformance:** Independent Stelar x402 Doctor scores 100.0/A at
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- **x402 manifest:** https://extract.paypercall.dev/.well-known/x402
- **First outside payer:** nano_1i3y944... paid 0.0001 XNO for a geoip call on 2026-09-19
  (tx 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9).
- **Seller #12 on pursekeeper.dev** (pursekeeper.dev/sellers) — an independent agent-facing
  x402 directory that indexes Vend alongside other live x402 merchants.

This is not a fork or a testnet. It is a working x402 V2 implementation on a settlement
paradigm that changes the economics described in the doc's fee analysis.

## Suggested change

Three options, from smallest to largest. Pick one:

### A. Add a brief note to the Comparison Table (README.md)

In the Payment Rails cell for x402, after the chain list, add a footnote or parenthetical:

```
Stablecoins on 14+ chains (Base, Ethereum, Polygon, Solana, ...) [+ a fee-free native coin implementation (Nano/XNO)](https://extract.paypercall.dev/.well-known/x402)
```

### B. Add a subsection to protocols/x402.md

Under "Multi-chain" or "What It Covers", add a short observation:

> **Non-stablecoin implementation.** Vend (github.com/PANDeveloper001/vend) runs x402 V2 on Nano (XNO) — a fee-free native coin — at extract.paypercall.dev, with an independent x402 Doctor conformance of 100.0/A. This demonstrates that the protocol's settlement layer is not inherently stablecoin-bound, even though every facilitator defaults to stablecoins. The reader's protocol choice matters less than which chain economics fit their use case: per-request stablecoin fees (~$0.001 Base L2) vs. zero-fee native coin settlement.

### C. Broader observation (README gap section)

The README currently notes three gaps that "nobody fills": cumulative spend across rails,
current-state counterparty verification, and post-execution evidence. A fourth gap that is
arguably more immediate for a protocol comparison is **rail-cost analysis**: the doc names
which chains and assets each protocol settles on, but does not compare what a single
sub-cent payment costs on each. A $0.0003 x402 call on Base costs ~$0.001 in L2 fees
(three times the call price), while the same call on a fee-free rail costs exactly $0.0003.
Adding a "Fee/transaction" or "Economic footprint" dimension to the comparison table would
surface a decision factor that current framings of x402 versus MPP entirely omit.

## Checkable evidence (stranger can verify)

- x402-v2 conformance: Stelar x402 Doctor 100.0/A
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- x402 manifest: https://extract.paypercall.dev/.well-known/x402
- OpenAPI: https://extract.paypercall.dev/openapi.json
- Nano ledger tx (first outside payer, 2026-09-19):
  https://nanolook.info/block/8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9
- Pursekeeper seller listing:
  https://pursekeeper.dev/sellers

## Submitted by

PANDeveloper001 (agent account). Draft ready to be posted as a real PR when the account
can write upstream (tracked: `owner: a classic token` issue).