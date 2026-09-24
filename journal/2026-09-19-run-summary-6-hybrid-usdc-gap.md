# Run summary: push landed, health verified, hybrid-USDC gap confirmed

2026-09-19 (evening). Vend.

## What this run did, in order

1. **Applied the corrective action** (last run "no progress" — actually two things were
   left unfinished: the directory index had 2 stale uncommitted files, and the last
   distribution commits had not been pushed to origin).
2. **Verified the server is genuinely healthy.** My first curl to extract.paypercall.dev
   timed out (health takes ~7.5s because of the live store probe; my 8s --max-time was
   borderline). Via `rai-par` the endpoints answer correctly: /health 200, / 200 fast,
   and 21/21 endpoints up. The earlier "outage" was a probe artifact, not a real outage.
3. **Pushed 3 commits to origin** (783913c, 6830e29 from the previous session, then a
   heartbeat/probe refresh): `rai-ship.sh status` now reports 0 to send, no divergence.
4. **Verified vend-client is pip-installable from the self-hosted URL.** A fresh venv
   does `pip install` the wheel at /static/packages and a dry-run geoip call returns the
   full x402 quote (price XNO, pay_to, resource, accepts). No PyPI needed for distribution.
5. **Probed the directory sweep.** Confirmed live listings for AgentBoard, Neuronto ARD,
   Vivioo, AgentMRR, MCP Registry (all 200). AgentNDX, MCPSafe and AgentShare returned
   200 *on their site* but do NOT confirm Vend is listed (home/submission pages only) —
   reverted those from "live" to "submitted" in the index rather than over-claim. The
   `rai-scope adopted` tool correctly reported `adopted: false` for them.

## The real finding: Vend's hybrid USDC rail is built, tested, and gated on one credential

The x402 directories that matter (402index, 402.ad, Satring, x402.nexus, CDP Bazaar)
reject Nano-only listings. Vend is *meant* to accept USDC-first where an index demands it
(AGENTS.md), and that code is already written and green:

- `cdp_verify.py`: `build_usdc_accept`, `price_usdc_to_amount`, `usdc_pay_to_address`
- `nano_verify.py` (L~282): when `VEND_USDC_ADDRESS` is set, the 402 challenge advertises
  a second `accept` (USDC-on-Base) alongside Nano
- `test_cdp_verify.py`: 12 tests pass, including "no USDC accept without env"
- Main suite: 5 tests pass.

The only missing piece is `VEND_USDC_ADDRESS` (a Base Treasury USDC address). Health
reports `cdp_bazaar: {configured:false, usdc_address:not_set}`. Enabling it is a
treasury/credential decision for the owner (which Base address, who holds the key) — not
something this run should improvise. Until then Vend cannot list on the USDC-only x402
directories, which is the largest remaining unopened distribution surface.

## Money (the number that settles it)

No paid calls this run. Runway position unchanged: no endpoint costs more than it pays.
