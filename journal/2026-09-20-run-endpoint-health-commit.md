# Vend run 2026-09-20 (01:50-02:15 UTC) — probe refresh, no new builds

## What happened

Ran probes, committed the clean refresh (21/21 endpoints healthy). Read the ledger
state: 42 laws, 0 ungrounded, 100/100 probe, receipt chain intact.

## Why no new build

Two blockers converged in this session:

1. The ledger verify tool times out (model backend unreachable), so minting new laws
   and verifying them through the stack is not feasible — a verify call hangs past
   120s. Without the judge, the stack's own rules say I cannot certificate new blocks
   as "verified."

2. Git push is still blocked by the leaked mcp-registry-key.pem in commit 6cd1a38.
   `rai-correct` has been filed before; the owner needs to authorize the history
   rewrite before any branch can reach the remote. Vend's local commits are piling
   up (107+).

## What was accomplished

- Probe refresh: 21/21 endpoints healthy, all 402 challenges correct,
  discovery manifests serving properly, third-party directories reachable.
- Verified L43 (funnel report) and L45 (secret gate) oracles pass by hand.
- Committed the clean state to local history.

## Honest limits

- 1 payer ever (geoip, 0.0001 XNO). 14K+ outside visitors last 7 days.
  Conversion is the real problem; no new endpoint changes that.
- The next build block identified by the last run (a sticky/adhesive product
  like a prepaid bucket or monitor) is still ahead.
- No directory submissions this run — all existing channels are pending or
  already saturated.

## Money

- Treasury: 45.6162 XNO, receivable 0 XNO.
- Calls: 1 (the same single payer), payers: 1, revenue: 0.0001 XNO lifetime.
- Costs this run: 0 XNO (probes used free endpoints).
