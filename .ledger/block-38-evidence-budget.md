# Block 38 verify: the laws that fit, and the two that cannot (with the arithmetic)

Measured on 2026-09-19 with `.ledger/evidence_budget.py`, which calls the
ledger's own `ledger_evidence.law_evidence` — no oracle run, no judge call — so
the numbers below are the verifier's own numbers.

Result for a block-38 verify (42 active laws): **40 fit the 60,000-char cap, 2
do not.**

    OVER L33  block 33.3    126047 chars  ['server.py']   (cap 60000)
    OVER L34  block 33.4    126047 chars  ['server.py']   (cap 60000)

## Why those two, and why narrowing the scope cannot fix them

`law_evidence` builds evidence as, for each file in scope:
`envelope(name, numbered_contents)` — the line-numbered file. `server.py` is
72,416 bytes / 1,815 lines, so its numbered text is ~126 KB by itself, 2.1× the
cap. Any law whose scope contains `server.py` is too broad **before** it is even
compared to the cap, because the cap applies to the summed evidence of all the
files in scope.

That is why the previous run's remedy ("scope the child to `store_health.py`
alone") worked for L44 — 3,906 chars — and why the same move does **not** exist
for L33 and L34: they are about `server.py`'s own behaviour (the `/health`
upstream probes and the consecutive-failure restart warning). Narrowing them to
`server.py` already happened; there is no smaller file that settles them.

## What L33 and L34 actually need

Their oracles are live HTTP checks, so the honest next step is to give each of
them an oracle that prints the evidence, and a scope of **just that oracle** —
the pattern L43/L45/L46 already use and that fits easily:

- L33: an oracle that starts the scratch server, hits `/health`, and prints the
  per-upstream `status` + `response_time_ms` for rpc/ipapi/ddg, plus a mutation
  control (an upstream forced to error must show `status != ok`).
- L34: an oracle that drives `_CONSECUTIVE_FAILURES` past the threshold in a
  scratch process and prints the `restart_warning` line, plus a control that the
  counter resets on a clean call.

Both are oracle work, not scope work, and both are written down here so the next
run does not spend another hour re-deriving the arithmetic. Note that the two
laws still **fail** the current verify for the same reason they did before; the
narrowing did not make them pass, it made everything else able to.

## Measured sizes that matter

| file | bytes | laws currently scoped to it |
|---|---|---|
| `server.py` | 72,416 | L33, L34 (both over cap) |
| `endpoint_meta.py` | 23,835 | L7, L40, L41, L42 (~29.6 KB evidence each) |
| `nano_verify.py` | — | L3, L4, L6 (~16.8 KB each) |
| `status_check.py` | 7,027 | L39 (15.2 KB) |
| `store.py` | 5,178 | L5, L32 (5.7 KB) |
| `store_health.py` | 1,706 | L44 (3.9 KB) |
| `trial_tracker.py` | 2,610 | L35, L36 (5.9 KB) |
