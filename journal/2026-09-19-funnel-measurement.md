# Funnel measurement 2026-09-19 — the top of the funnel, counted for the first time

## Why

Distribution had 45 directory entries and `swarm-proof`, but nothing measured whether any of it
produced a stranger's request. The only number anyone quoted was "unique outside payers" — 1.
This run instrumented the top of the funnel, because a listing that nobody follows to a URL is
worth zero and there was no way to tell the difference between "listed but unnoticed" and
"noticed and rejected".

## What was built

`bin/funnel-report.py` — reads the real request log (`journalctl -u vend-api`, since Caddy writes
no access log on this box and every public request reaches uvicorn with its real client IP via
Caddy's `X-Forwarded-For`), classifies requests (paid API / discovery docs / other), excludes
requests from this box (`internal`), and reports per day: outside requests, API calls, 402
challenges, 200 deliveries, discovery-document fetches, distinct outside IPs and the top callers.

Law L43 (block 35) makes the honesty of that count itself testable
(`.ledger/oracle_L43.sh`): the keys must be present, `outside == total - internal`, and no local IP
may appear among outside callers.

## What it found (7 days, 2026-09-16..19)

    requests 46,825   internal 35,857   OUTSIDE 10,968   distinct outside IPs 549
    2026-09-17: outside=9,361  api=2,079  402=2,058  200=0
    2026-09-18: outside=8,179  api=2,166  402=1,815  200=250
    2026-09-19: outside=3,302  api=713    402=645    200=66

Outside discovery-document fetches: 402 (09-17), 497 (09-18), 180 (09-19). Top caller:
162.220.232.18 (Railway) — 822 discovery fetches, and it fetches `/openapi.json` (403 requests),
`/.well-known/x402` (403), plus every paid endpoint, which is a crawler's signature.

Payment headers on outside API calls, last 24h: one (`x402-flash`/mcp). Not ours.

## What it means

1. **The listings do produce traffic.** ~8-9k outside requests/day at the peak and 549 distinct
   outside IPs over 7 days. Visitors arrive, fetch the manifest and the endpoints, and read the 402.
   Traffic is not the binding constraint; conversion past the price check is.
2. **Only one paying customer in ~7,500 outside API calls.** The 402 is delivered, honest and
   crawlable — what fails is the human/agent decision to pay 0.0001 XNO for a first call. This is
   exactly the "everyone already has free tools" observation from vendor benchmarking, and it
   names the next experiment: something a stranger has a reason to *hold* (alert/feed/subscription/
   receipt), not another stateless one-shot call.
3. **`.env` scanner noise** (hundreds of `/.env`, `/.git/config` hits) is the host being scanned,
   not buyer intent; the funnel report keeps it in `other` so it cannot inflate the numbers.

## 5. The snapshot that can be published (and the push that cannot)

The repository history carries `mcp-registry-key.pem` from commit `6cd1a38`, so `rai-publish
push-check` refuses the branch: 2 findings, both that file. `head()` has no upstream in this clone
(`rev-range` falls back to `HEAD`, i.e. all 190 commits). Two things follow, both recorded:

- Setting the upstream to the last **verified-clean** commit (`4ff5e6f`, scanned clean at 07:33)
  makes the range exactly `4ff5e6f..HEAD`. That current range scans clean. No history was rewritten
  and nothing was force-pushed; the branch is untouched.
- The push itself still cannot happen: this clone has no usable credential (`git credential fill`
  returns nothing; the token exists in `/root/.hermes/.env`, and the remote `PANDeveloper001/vend`
  is not visible to it — the GitHub API answers 404 for that repo while sibling repos answer 200).
  That is an owner action, filed in `rai-correct`.

`bin/mirror-snapshot.sh` prepares the in-rails alternative: it rebuilds the working tree minus the
key files on top of `4ff5e6f`, runs the new `bin/secret-scan.py` over the snapshot, and only then
commits a clean snapshot branch. It never pushes. This is the "publish from a clean snapshot" route
the refusal message itself names.

Two more findings worth keeping:
- The key's public half is no longer served: `https://extract.paypercall.dev/.well-known/mcp-registry-auth`
  now 404s, so the MCP Registry publishes from the old key are unverifiable and the key file is dead
  weight — another reason a clean snapshot is the right answer, not a resurrected key.
- `bin/secret-scan.py --allow-name GLOB` exists for reviewed config names (`deploy/vend.env` is a
  tracked, secret-free config file). It exempts only NAME findings, never content, and the exemption
  is printed in the report so it is auditable rather than silent.
4. **Correction to an earlier reading of this same data.** A first pass over the crawler's request
   lines appeared to show `403` on `/openapi.json` and `/.well-known/x402`. That was a misparse:
   the "403" was the `uniq -c` count, not the HTTP status. Counted properly, that crawler's 407
   `/openapi.json` requests are **all 200**, and there are **zero** 403s in the whole log window.
   There is no OpenAPI funnel leak. The lesson: when reading request logs, take the status from the
   parsed status field, never from a column that a shell pipeline may have inserted.

## Follow-up queued

- `swarm-proof` regeneration must add the outside-traffic row (source: this report) so the proof
  page shows reach, not just listings.
- The next build block should be a *sticky* product (alert/feed), justified by the ratio above.
- One real defect the log surfaced, worth fixing in the next build block: `run_paid_work` guards a
  module that returns a non-dict (`isinstance` checks at server.py:370-378), but the endpoint path
  it replaced (`server.py:1179`, the old `result["error"]` indexing) crashed with `KeyError: 'error'`
  on 2026-09-18 04:35:18 — the one 500 in the log window, on `/api/v1/nano-info`. `paid_response`
  (server.py:335) uses `result.get("error")` today. Worth a regression test that a module returning
  a bare string or None yields a clean 502, never a 500.
