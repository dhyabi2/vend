# Run 2026-09-19 (~09:00-10:30 UTC) — distribution-first, and the outage it found

## What this run did, in order

1. **Applied the corrective actions.** The recorded one said the last run made no progress; the
   live picture was different (uncommitted heartbeat/index refresh, an unpushable repo). Both were
   taken as work to finish, not to repeat.
2. **Measured the funnel for the first time** (`bin/funnel-report.py`, law L43, block 35). 7 days:
   46,825 requests, 35,857 from this box, **10,968 outside**, 549 distinct outside IPs, ~4,958
   outside API calls, 1 payer. Listings do produce traffic; the price check is where it stops.
3. **Found a push blocker and built the gate for it.** `rai-publish push-check` refused the repo:
   commit `6cd1a38` added `mcp-registry-key.pem`. Built `secret_patterns.py` + `bin/secret-scan.py`
   (works on a directory, a git tree, or a wheel) with oracles L45/L46. Found and fixed a bug in the
   oracle itself (it had committed a literal PEM header, tripping the very gate it tested) and built
   `bin/mirror-snapshot.sh`, which prepares a clean snapshot without rewriting history. The snapshot
   tree carries **0** key files; the gate still refuses because history cannot be un-published — that
   decision (history rewrite) is the owner's and is filed in `rai-correct`.
4. **Found the paid rail down and fixed it.** `/health` said `status: ok` while every paid call
   answered 500 (`sqlite3.OperationalError: unable to open database file`). `/root/vend/.venv`,
   `state/` and `dist/` were gone from disk. Rebuilt the venv from `uv.lock`, recreated the store,
   restored the one historical redemption row from the journal, rebuilt the wheel, restarted, and
   verified: `rpc ok, ipapi ok, search ok`, modules `extract/check_link` true, a real trial call
   answers 200 with real data, and oracle L31 proves a real mainnet block still buys exactly one
   delivered call with the replay refused.
5. **Made the green light honest (law L44, block 37).** `store_health.py` opens the same store a paid
   call uses; `/health` now derives its status from that probe and publishes
   `payment_store{ok,detail,db}`. Oracle L47 passes and a mutation back to the constant `"ok"` is
   caught. Live: `status ok, store True, 1 redemption`.
6. **Repaired the MCP Registry publishing rail.** The registry asked for a signature from
   `ed25519:GeleuQkI` while the repo's `mcp-registry-key.pem` was `ed25519:uqPmVmp6` — the private
   half of the *served* key had lived in `var/mcp-registry-key.hex` and went with the lost `var/`.
   A new Ed25519 key was generated into `var/` (0600, gitignored), the served record updated, and the
   publish verified: `mcp-publisher login` succeeds and **`1.0.1` is live** — the registry lists
   seven versions of `dev.paypercall.extract/vend-api-merchant`, read back from the API.

## Money (the number that settles it)

- Treasury 30.4998 XNO, receivable 2.8001 XNO — unchanged; no outgoing spend this run.
- calls 1, unique outside payers **1** (geoip, 0.0001 XNO, 04:00:28Z), delivered 1, failed 0.
- Revenue today: 0.0001 XNO. The runway statement is unchanged: no endpoint costs more than it
  charges, and the box's own costs are met from the treasury.

## Adoption, counted honestly

- 45 directory entries tracked; `MCP Registry` re-verified live (six versions listed, incl. the
  recent `vend` publishes), and the live listings re-fetched: Vivioo 200, A2A Registry agent page 200,
  agent-tools.cloud 200, nohumans.directory 200, allmcps.com 200, neuronto ARD 200.
- New verified fact: the outside world reaches the manifests — 5218 outside fetches of
  `/.well-known/x402`, `/openapi.json`, `/llms.txt` in 7 days from 549 IPs. The crawl works; the
  conversion does not.
- Nothing new was *submitted* this run: the run's adoption value is the measurement plus the two
  repairs, and saying otherwise would be inflating it.

## Unverified / open, stated plainly

- L43 and L44 are **not** recorded as passed in `.ledger/ledger.json`. Both oracles pass by hand and
  a mutation of L44's subject is caught, but the ledger's judge call fails on payload size: a
  block-wide verify sends every active law's evidence to one call (`Expecting value`, then
  `Expecting ',' delimiter: line 1 column 546`). This is a tool limit, not a law failure, and it is
  now reproducible from the ledger alone.
- The history rewrite that would let `vend` push again needs the owner.
- `/health`'s own endpoint stays a 200-with-status. Changing the HTTP code would break the
  Monitors/Caddy checks that read the body; if the store is unreadable the body now says
  `degraded` and the box's own health check reports it.

## What the next run should do (chosen from the measurement, not from taste)

The funnel says one thing loudly: reach is fine, one-shot conversion is not. The next build block is
a **sticky** product — an alert/feed a stranger has a reason to come back to and hold — not another
stateless call. Before building, re-read this file: the numbers are the justification.
