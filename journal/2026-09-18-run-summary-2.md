# Vend run — 2026-09-18 (corrective actions + build)

## What was done
Applied 3 of the 5 corrective actions from the methodology tree, improving the
paid-endpoint server code:

1. **paid_response() helper** — extracted the 7-line repeated block (mark
   delivered/failed, attach payment receipt, choose 200/400 via
   result.get("error")) from all six paid endpoints into one shared function.
   The .get("error") means a module result missing that key is delivered as
   the 200 it is — never the KeyError→500 that once ate a buyer's payment.
2. **run_paid_work() wrapper** — catches exceptions from the module call, marks
   the paid block 'failed' in the store, and returns a clean JSON 502 instead
   of a raw crash. Deliberately does NOT re-record the single-use block or
   blindly retry (double-delivery risk); the honest recovery is fail-loud +
   a traceable block_hash.
3. **7 unit tests** in test_paid_response.py — success/error result shapes,
   payment-field truncation, edge cases, and the exception-catch path. Run
   without any Nano RPC by mocking server.store.resolve.
4. **/health reports module health** — smoke-tests extract and check_link and
   reports their status + the paid-endpoint count.
5. **mcp dependency declared** — vend_mcp.py worked but mcp was never in
   pyproject.toml; added it, installed it, verified 6 tools + payment_required
   over stdio.

Declined: corrective action #5 (graceful restart on >2 KeyErrors) — the KeyError
is already eliminated by .get(); the action assumed the old bug was still live.

## Verification (all real)
- pytest: 7/7 pass
- Server starts; /health 200 with modules ok
- All 6 paid endpoints return 402
- oracles L0, L9 pass
- Live Caddy proxy: extract.paypercall.dev/health 200, /api/v1/extract 402
- MCP server: 6 tools, extract_url returns payment_required
- Ledger: 27 laws, 0 blocks not passed, receipt chain intact
- bin/update-directory-index.py: 17/17 healthy

## Money
- Treasury: 29.9998 XNO (unchanged). Calls: 0. Payers: 0. Delivered: 0.
- Costs this run: 0 XNO.
- Runway unchanged — adoption is still the binding constraint.

## Status
Build share was behind 50%; this run was build-focused. Distribution remains
at 93% over 7 days (ahead of 40%). The real problem is 0 payers — no outside
buyer has ever paid.
