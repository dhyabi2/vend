# Vend run 2026-09-19 (09:00-09:45 UTC) — what happened, what is verified, what is not

## Blocks

### Block 35, law L43 — the funnel report (VERIFIED via judge-under-test)

Built `bin/funnel-report.py`, minted L43, wrote `.ledger/oracle_L45.sh`-style oracle
`.ledger/oracle_L43.sh`. Oracle passes:
`PASS: source=journalctl -u vend-api total=46903 internal=35919 outside=10984 outside_ips=549`.

The `ledger verify` path crashed with the known provider failure
(`RuntimeError: model call failed: Expecting value: line 1 column 1 (char 0)`), so the law was
proven with a **judge under test** instead: exactly the tool's prompt shape
(`/root/invent-stack/bin/ledger_judge.py::_ask`), the real evidence envelope (9163 chars, numbered
`bin/funnel-report.py` + the oracle run block), `deepseek/deepseek-v4-pro-0813` at
`reasoning.effort=medium`. Returned `L43 pass=true` with a quoted proof and `pass=false` on the
decoy token law — the control the stack requires. This is a *reproduced* judge verdict, not a
recorded one; the ledger entry stays pending until the tool itself can run.

### Block 36, laws L44/L45 — the pre-publish secret gate (TOOL-VERIFIED, ledger pending)

On 2026-09-19 `rai-publish push-check` refused the repository: commit `6cd1a38` added
`mcp-registry-key.pem` (a private key) and it is in the tracked tree, so **every push of HEAD is
blocked**. Earlier the same day at 07:33 the same scan was clean over 182 commits — the key landed
after that.

This is the stack's own rule ("when a tool or capability is missing, invent the extension, never
weaken the rail"). What was built:

- `secret_patterns.py` — one home for the rules, so `.gitignore` and the gate cannot drift.
  Cheap and safe now: a false positive that refuses a push is a fail-closed accident, a false
  negative publishes a key.
- `bin/secret-scan.py --repo <dir|wheel> [--tree]` — scans a build artifact (wheel/sdist/zip) or the
  git-tracked tree, exits 2 on findings.
- `.ledger/oracle_L45.sh` passes: refuses a leaked `mcp-registry-key.pem`, refuses a GitHub token
  hidden inside a built `.whl`, passes a clean snapshot and passes the real release wheel
  (`dist/vend_client-0.1.0-py3-none-any.whl`).

**Not done, and deliberately so:** the history rewrite. `git filter-repo`/`filter-branch` to drop
`6cd1a38`'s key file was not run and was not pushed: the agent's standing rules say no force-push
and no history rewrite, and a rewrite of four already-committed runs was judged riskier than the
alternative. The safe correction is the one the gate itself prints — publish from a clean snapshot
(the release wheel is already clean) — plus `rai-correct` asking the owner to authorise the rewrite.
Until then, pushes stay blocked; that is reported, not hidden.

Unrelated finding while scanning: `deploy/vend.env` is tracked and matched the loose `.env.` rule.
Its actual contents are host/port/price settings only (no key, token or secret). The rule was
tightened to `.env.<environment>` names and the file is left tracked.

## Money

- Treasury: 30.4998 XNO, receivable 2.8001 XNO (neither moved today).
- Paying customers: 1, geoip, 0.0001 XNO, 2026-09-19T04:00:28Z. Nothing new since.
- Cost per call: unchanged; no endpoint costs more than it charges.

## Funnel (the number that matters for adoption)

7 days: 46,825 requests, 35,857 internal, **10,968 outside**, 549 distinct outside IPs, 4,958
outside API calls, 1 payer. Reach is real; conversion past the price check is not happening.
Full analysis with the correction about the mis-read "403" is in
`journal/2026-09-19-funnel-measurement.md`.

## Unverified / open

- L43 and L45 are *not* recorded as passed in `.ledger/ledger.json`; the judge backend is flaky for
  the tool's call path (not for direct calls). Both have oracle scripts that pass by hand.
- The history rewrite of `6cd1a38` needs the owner (`rai-correct` filed).
- Next build block, chosen from the measurement: a *sticky* product (alert/feed/subscription),
  because a one-shot 0.0001 XNO call is exactly what the free tooling already gives away.
