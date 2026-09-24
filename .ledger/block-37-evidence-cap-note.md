# Block 37 verify is blocked by the tool, not the law — evidence

Reproduced three times on 2026-09-19 with `LEDGER_HTTP_TIMEOUT_S=240 LEDGER_RETRIES=4`:

    FAIL L44
      L44 needs 131787 chars of evidence (cap 60000); narrow its --scope or split the law

Facts:
- `ledger list` shows L44's scope as `store_health.py` (the amendment reported
  "amended L44 to version 3"), but `ledger.json` still carries `['server.py','store.py']`
  and the amend command now refuses with "already amended 2 times; split the block instead".
- `server.py` alone is 72,416 bytes (numbered ~85 KB), so any scope containing it
  exceeds the 60,000-char evidence cap no matter how the law is written. This is the exact
  failure mode already recorded in the skill for earlier blocks.
- Block 37's verify batches every active law into one judge call, and the call also fails
  on its own (`RuntimeError: model call failed: Expecting value: line 1 column 1 (char 0)`
  / `Expecting ',' delimiter: line 1 column 546`), which is the provider-size failure the
  skill documents.

What is true regardless: oracle L47 passes (healthy store reported ok; an unopenable store
reported unhealthy with the reason; a mutation that restores the constant `"ok"` is caught,
1 FAIL, non-zero exit), and the live `/health` answers
`status ok, payment_store ok, rpc ok, ipapi ok, search ok`.

Next run: split block 37 (the ledger's own remedy) and scope the child to
`store_health.py` alone before verifying.
