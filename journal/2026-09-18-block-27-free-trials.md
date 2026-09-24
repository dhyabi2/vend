# Block 27: Free trial calls (real data, 5/IP/day) for all endpoints

## What was built

Replaced the fake sample-data demo with a real free trial system:

**`trial_tracker.py`** — In-memory free trial tracker (thread-safe, rolling 24h window):
- Tracks free calls per IP address
- 5 free calls per IP per rolling day (configurable via `VEND_FREE_TRIAL_LIMIT`)
- Auto-prunes calls older than 24h
- Singleton pattern shared across all endpoints

**`server.py` changes:**
- `require_payment()` now checks trial eligibility BEFORE returning 402
- First 5 calls per IP bypass payment and return real data from the real module
- Trial calls get `payment.free_trial=True`, `payment.trial_remaining=N`, `payment.trial_limit=5`
- HTTP headers `X-Trial-Remaining` and `X-Trial-Limit` on every trial response
- `/api/v1/demo` now redirects (307) to the real endpoint with a sample query — agents get real data from their first call
- Old hardcoded demo data (300+ lines) removed

## Market context

This directly addresses the #1 finding from the x402 ecosystem gap analysis (Aug 2026):
- "Zero of 18,986 x402 endpoints publish an A2A Agent Card" (fixed by having the x402 manifest instead)
- "Agents need free trials — endpoints that let agents test before paying win the first call"
- "76% of x402 endpoints are dead" — Vend's 16/16 probe score makes it one of the most reliable

## Verification

**Unit tests (31/31 pass):**
- 5 `test_trial.py` tests: basic tracking, exhaustion, per-IP isolation, rolling window, singleton reset
- 26 existing `test_paid_response.py` tests all pass with the updated `paid_response()` (trial_info dict guard)

**Live probe:**
- `curl http://127.0.0.1:8402/api/v1/geoip?ip=1.1.1.1` returned HTTP 200 with real data (Australia, Cloudflare, real ISP)
- `x-trial-remaining: 3` header present (after consuming 2 on the loopback IP)
- After 5 calls from same IP, returns 402 `payment_required` as expected
- Different IP gets fresh 5-call allowance

**Laws minted:**
- L35: Free trial: any IP gets 5 real-data calls per day across all endpoints without paying
- L36: Free trial returns real module data, not fake/demo data
- Both verified MANUAL (live curl probes + unit tests)

## Money

Treasury 30.4998 XNO, 0 payers, 0 paid calls (unchanged). Free trial calls do not consume treasury.

## Learned

- Inserting a trial check into `require_payment()` before the 402 generation was the right approach — zero changes to individual endpoint handlers
- The `paid_response` function's `getattr(request.state, "trial_info", None)` returns a `MagicMock` when the request is a test mock, not `None` — fixed with `isinstance(trial_info, dict)` guard
- Localhost (127.0.0.1) is the IP seen by trials from this box; Caddy proxies real IPs from outside
- The market intelligence from minia2a/Dev.to was actionable: "offer free trials" was the #1 recommendation, and building it took one focused block