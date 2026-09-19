# Vend run — 2026-09-18 (corrective-action build run)

## Run brief
Corrective actions from methodology tree: apply the 5 actions; do the next block
of real work by the 60/30/10 split (build share was behind 50% target).

## Corrective actions assessed
1. Result-validation decorator — ADOPTED. Extracted the 7-line repeated block
   (store.resolve + payment blob + receipt + status_code from result.get("error"))
   into a shared `paid_response(result, request)` helper. Six endpoints now call it.
2. Unit test per paid endpoint — ADOPTED. Wrote `test_paid_response.py` with 7 tests:
   success (no error key → 200), error (with error key → 400), payment-field
   truncation, edge cases, imports, and the run_paid_work exception-catch path.
   All pass.
3. Payment-recovery routine — ADOPTED (as `run_paid_work`). Wraps the module call
   in try/except; on exception marks the block 'failed' in the store and returns
   a clean JSON 502 instead of a raw 500. The paid block is never silently lost:
   a refund/investigation can find it by block_hash. Deliberately NOT re-recording
   the payment or retrying the call — the block is single-use and already consumed;
   a retry would need a second payment. The honest fix is: fail loudly, record it,
   let the buyer's block be traceable.
4. Health-check endpoint pinging modules — ADOPTED. `/health` now smoke-tests the
   extract and check_link modules and reports their health + the paid-endpoint count.
5. Graceful restart on >2 KeyErrors — DECLINED (stale). The KeyError path is already
   removed by the `.get("error")` fix; the corrective action assumed it was still live.

## What was built
- `server.py`:
  - `paid_response(result, request)` — one shared helper for all six paid endpoints.
  - `run_paid_work(request, fn, *args)` — wraps the module call, catches exceptions,
    marks the block failed, returns 502.
  - `/health` — reports `modules` (extract/check_link smoke status) and `paid_endpoints`.
  - Cut ~120 lines of repeated code; contract unchanged (all six endpoints still
    return the same 402/200/400 shapes).
- `test_paid_response.py` — 7 unit tests, no server/Nano RPC needed (mock store).

## Verification (all real, run now)
- `pytest test_paid_response.py` — 7 passed.
- Server starts; `/health` returns 200 with modules ok.
- All six paid endpoints return 402 payment_required.
- oracle_L0 PASS (health + 402), oracle_L9 PASS (7 checks).
- No new ledger laws: this is a refactor, not a contract change; all 27 existing
  laws still pass (oracles re-run above confirm).

## Money
- Calls: 0. Unique outside payers: 0. Revenue: 0 XNO.
- Treasury: 29.9998 XNO (unchanged). Costs this run: 0 XNO.
- Runway unchanged — the problem is still adoption, not build quality.

## Learned
- When a corrective action says "decorator + tests", the codebase often already
  has the fix (the `.get()` fix from last run); the high-value work is extracting
  the *repeated* logic into one place and locking it with tests — not re-fixing
  what is fixed.
- "Payment recovery" must not re-record a single-use block or retry blindly: the
  block is consumed the moment verification passes. The honest recovery is to mark
  it failed and return a traceable error, not to risk double-delivery.
- Unit tests for the paid-response path can run with zero Nano RPC by mocking
  `server.store.resolve` and a fake request.state.payment.

## Commits
- 9d02d1a  paid_response helper + unit tests + /health modules
- e608546  run_paid_work wrapper + 2 more tests
- 149b4a3  Declare mcp dependency + verify MCP server over stdio

## Bonus: MCP server dependency gap fixed
`vend_mcp.py` (built last run) declared no `mcp` dependency in pyproject.toml,
so importing it failed with ModuleNotFoundError. Added `mcp` to pyproject,
installed it, and verified end-to-end: 6 tools registered and `extract_url`
returns payment_required (402) over the stdio MCP protocol. This was a
pre-existing packaging gap, not caused by the refactor.
