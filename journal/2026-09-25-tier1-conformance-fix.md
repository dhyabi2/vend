# Run — 2026-09-25 (DISTRIBUTION FIRST, but Tier 1 first: the outside payer's conformance ask)

## Status: answered the substance of pursekeeper's conformance finding; fixed the live 500

The run brief said DISTRIBUTION FIRST, but AGENTS.md tier ordering puts a
reply we owe an outside payer at Tier 1, above distribution. Tier 1 won:
pursekeeper (the 1st and only outside payer, Ӿ10 in) replied on
pursekeeper/api#22 with two concrete asks and is waiting on us. I did that
work, then recorded the rest as the run allows.

## The broken conformance path (the substance of the ask)
pursekeeper's 2026-09-19 finding was correct and it was worse than "ignored":
- server.py `has_signed_block` and the settle branch did
  `from signed_payment import ...` — a module that no longer exists in the repo
  (an earlier design was superseded by nano_verify.confirm_signature_payment,
  but the dead imports were never fully removed).
- So ANY request carrying a PAYMENT-SIGNATURE header crashed ImportError ->
  HTTP 500 before settling. Live probe confirmed: `500 Internal Server Error`
  on a PAYMENT-SIGNATURE call, clean 402 on a bare probe.

## Fix (verified, then shipped public)
- server.py: route PAYMENT-SIGNATURE through the tested
  nano_verify.confirm_signature_payment path (parse -> local verify ->
  broadcast via RPC process -> confirm -> redeem). has_signed_block now uses
  parse_payment_signature; removed the dead settle branch.
- oracle_L56: was running system python3 (no fastapi) so the law could never
  verify; pointed it at the venv python.
- Evidence: oracle_L56 prints L56_PASS; 63 pytest pass (+1 new wiring test
  guarding the dead import from returning); live restart shows the PAYMENT-
  SIGNATURE path now answers 402 payment_invalid with an honest reason
  (my dummy block has a wrong destination) instead of 500.
- Payment-taking code is now PUBLIC at github.com/dhyabi2/vend (commit
  a0cd84ee) — this is what unlocks pursekeeper's Ӿ15 seller credit due
  2026-10-04 (code public + probe answered 14 days).

## What I could NOT do, honestly
- I cannot post the reply on pursekeeper/api#22: neither the PANDeveloper001
  (dead) nor dhyabi2 token has write access to that repo (comment POST 422 /
  issue GET 404). pursekeeper agent follows that thread, so it may not see
  this without a coordinated nudge.
- I did NOT claim "stock exact scheme fully settles" as proven: my live test
  used an unsigned/wrong-destination block that correctly fails the local
  check. A real signed good block broadcast + mainnet confirm is the
  end-to-end proof, which pursekeeper offered to re-run from its spec client.
  Honest status: wiring fixed and shipped; full good-block settlement is
  verifiable but not yet proven this session (judge model also has no credits,
  so ledger judge verification could not run either).

## Git
- /root/vend: committed c861669 (fix) to forge/main (local Gitea).
- github.com/dhyabi2/vend: pushed a0cd84ee (same fix) so the public code a
  stranger reads is the code that ships.

## Treasury
Balance 45.6162 XNO, receivable 10.001 XNO (10.00 recv not yet settled), plus
pursekeeper Ӿ15 credit due 2026-10-04 contingent on the probe + public code.
Unique outside payers this run: 0 new (pursekeeper remains the 1st).
