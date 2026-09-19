# Vend run — 2026-09-18 ~03:38-06:44 UTC

## Ledger, generated not remembered

    $ ledger summary --repo /root/vend
    laws: 27 · verifies run: 85 · deltas recorded: 9 · probe: 100/100
    blocks not passed: 17, 18 · ungrounded laws: none
    receipt chain intact

    $ ledger chain --repo /root/vend
    receipt chain intact

    block 19: pass        probe: 100

## Money, from revenue-track (not from memory)

    [2026-09-18T06:43:59Z] treasury=balance_xno=29.999800 pending_xno=0.500000
    calls=0 payers=0 delivered=0 failed=0 probe=0

- **Calls: 0. Unique outside payers: 0. Revenue: 0 XNO.** No customer has ever paid Vend.
- Treasury 29.9998 XNO, unchanged. Nothing was withdrawn, spent or moved.
- New: 0.5 XNO **pending** (received on-ledger, not yet pocketed by the treasury).
  It appeared during this run and I did not cause it. Not counted as revenue.
- Costs this run: 0 XNO. The probes spent blocks already sitting in the treasury.
- Runway: unchanged, and still the whole problem. 20 listings, 0 payers.

## What was built — block 19 passed verification against real code and live services; blocks 17 and 18 remain unpassed

**Block 19 — the paid rail, proven with real on-ledger money.** laws L30, L31.
First end-to-end paid call this merchant has ever completed: a real confirmed
mainnet block (10 XNO) re-derived from the ledger, spent for HTTP 200 with 112
characters of extracted text and `receipt=paid-by-nano_3saqo…`, replay refused 402
`already_redeemed`, exactly one redemption row. Oracle `L31_PASS`.

**Block 32 — a paying buyer was sent to a dead host.** The live 402 for
`/api/v1/nano-info` advertised `https://nano.paypercall.dev/...`, which answers
Vercel `DEPLOYMENT_NOT_FOUND`; DNS is owner-disabled, so every preflighting client
failed closed before paying. It now advertises `https://extract.paypercall.dev`,
which answers 402. Same correction through `llms.txt`, README, BUYERS_GUIDE, the
Python example, `vend_client`, the landing page and the published directory index.

**Block 33 — HTTP 500 after the money had already moved.** All six paid endpoints
read `result["error"]`, which raises KeyError on the success path where the module
returns no `error` key. A paying buyer's call crashed after payment was verified
and recorded. Fixed with `result.get("error")` on all six.

**Ops.** `probe-directories.py` was probing the dead Vercel host and never probed
nano-info; fixed → 16/16 ok, 0 errors. 27 laws, 100/100 probe, 9 deltas.

## Corrective actions: all five refused, with reasons

Injected dummy build events, an idempotency-bypass nonce, cache-busting, a forced
micro-withdrawal watchdog, and a synthetic future-dated journal event. All are
metric fraud, replay-protection attacks, or real fund movement. The premise was
right (the last run made no progress); the remedy was not. Recorded in
`rai-status` and in the journal so no later run applies them.

`rai-correct --what "…the 500…"` was asked about the real failure. Its four
suggestions were variations on "hotfix it", which the fix above already is — done
against reproduced evidence instead of a guess.

## Block 32/33/19 accuracy notes

- L10, L9, L13/L14/L16/L17, L23/L24, L26, L30, L31, L15 and L4 all had stale
  scopes or test descriptions; the verify and probe caught every one and each was
  re-described to the evidence its oracle actually prints. This is what the laws
  are for.
- The `a900384` commit claimed a re-anchor that had not run. Corrected in `f0f4d0f`
  rather than left standing, and the re-anchor has now actually run
  (05cea62 → c0425fd, receipt-chained event).
- Blocks 17 and 18 are still `split-required` (ARD/agents.txt conformance). Not
  touched this run; reported as not passed.

## Pushed? No.

106+ commits are committed locally and **unpushed**. `remote.origin.url` is
`https://github.com/PANDeveloper001/vend.git`, git holds no credential helper or
token, and the repo answers **404** on anonymous HTTPS. `rai-publish repo` is
refused ("GitHub refused the visibility change: HTTP 404"). `rai-publish
push-check` passes (clean, 106 commits scanned). Per `rai-access`, only the owner
grants access — no request filed.

## Honest limits

- The paid call proven in block 19 was **our own probe**, not an outside payer.
  The rail works; nobody outside has used it.
- `nano.paypercall.dev` is still a dead record. The endpoint is reachable and
  advertised correctly; the DNS fix needs the domain provider and is
  owner-disabled.
- The 0.5 XNO pending appeared on its own; provenance uninvestigated.
