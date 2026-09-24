# Incident 2026-09-19 ~09:35 UTC — the paid rail was down; found by the funnel work

## Symptom

`/health` had been reporting upstreams as
`{"rpc": "error: [Errno 2] No such file or directory", "ipapi": "error: [Errno 2] No such file or directory"}`
and `module_errors: {extract: 16-24, check_link: 16-24}`, while `status: ok` and the module flags
read `true` before the probe re-ran. Every paid call answered **500 Internal Server Error**:

    sqlite3.OperationalError: unable to open database file
    File "/root/vend/server.py", line 1634, in geoip_endpoint
        return run_paid_work(request, geoip_lookup, ip)

The free trial path even logged `TRIAL: ... used free trial (4 remaining)` and then the call died
anyway, so a stranger clicking a listing saw an error page, not a price.

## Root cause

`/root/vend/.venv` and `/root/vend/state` were **gone from disk**. The `vend-api` process (pid
340882, started 00:24) was still alive with its Python modules already imported, so it kept serving
routes and health, while `store.py`'s `sqlite3.connect("state/vend.sqlite3")` could no longer create
or open the file. Nothing in this run deleted them (`git status` clean at 08:5x; `state/` is
gitignored, so it was never in a commit); the most likely cause is an earlier in-cycle `uv`/staging
step. What is *measured* is the state, not the cause.

## What was done

1. `uv sync --frozen` rebuilt `.venv` from `uv.lock` (plus `pytest`, `ddgs`, `trafilatura` for the
   test suite) — the exact dependency set the lockfile pins.
2. `store.init()` recreated `state/vend.sqlite3`, and the one historical redemption row
   (`8546D8DF…FAD9`, geoip, delivered, 0.0001 XNO, 2026-09-19T04:00:28Z) was restored from its
   verbatim record in `journal/2026-09-19-first-payer-milestone.md`, so the money trail is intact:
   `bin/revenue-track` reads calls=1 payers=1 delivered=1 again. The row is meaningful as history
   and as replay protection: that block hash is spent and can never buy a second call.
3. `systemctl restart vend-api`, then verified: `/health` reports `rpc: ok`, `ipapi: ok`,
   `extract/check_link` true; a real trial call on `geoip.paypercall.dev` answers 200 with real data.
4. `.ledger/oracle_L31.sh`'s unpaid probe carried input, so on a trial-eligible localhost it answered
   200 and the oracle reported 4 false failures — the superseded-law trap already documented for
   L6-L20. It now probes bare, and L31 passes end to end: a real mainnet block bought exactly one
   delivered call and the replay was refused `402 already_redeemed`.

## The honest lesson

`/health` said `status: ok` while every paid call returned 500. A health check that reports on
upstreams and modules but never exercises the payment store is a green light on a red rail. The next
build block should add a store probe to `/health` (`state/vend.sqlite3` writable, `redemptions`
readable) and a law that `/health` goes non-ok when the store is missing — a health endpoint that
cannot see its own database is worth less than a 500, because it hides it.

Second lesson: `[Errno 2] No such file or directory` on an HTTP probe is a *local* failure
(missing module/binary), not a remote one. It was logged for days and read as a network blip.
