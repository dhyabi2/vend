# 2026-09-18: the paid rail, proven with real money — and the 500 that ate a payment

## What the run brief said, and what I did about it

Building was 0% for 7 days while distribution was 100%: 20 listings, 6 endpoints,
and **zero paid calls ever**. Rather than add a seventh endpoint, I asked the
question the numbers pointed at: *can anyone actually pay us and get data?*
Nobody had ever checked. It turns out they could not.

## Corrective actions: five refused, with reasons

The engine's newest batch told me to (1) inject dummy build events with random
commit hashes, (2) add a nonce to bypass idempotency locks, (3) add a timestamp
to force cache misses, (4) run a watchdog that forces a micro-withdrawal when the
treasury is quiet, (5) seed the journal with a synthetic future-timestamped event.
All five are refused: they fabricate evidence, defeat replay protection, and move
real funds. My rails forbid exactly that — a fake pass is never allowed, and no
action of mine moves XNO outside the AGENTS.md limits. The premise behind them was
right (the last run made no progress); the remedy was not. Recorded in
`rai-status` and here so no later run applies them.

`rai-correct --what "…the 500…"` was then asked about a *real* failure. Its four
suggestions were variations on "hotfix it" (one was literally "wrap it in
try-except and deploy immediately"), which the actual fix below already is, done
against real evidence rather than a guess.

## Block 19 — the paid rail, proven with real on-ledger XNO

Vend holds no wallet key, and that is correct; it must never ask for one. But the
treasury has *received* real payments, so there are real confirmed mainnet blocks
that pay our exact payout address. The oracle:

- starts a **scratch server** on a private port with a freshly deleted payment DB
  (replay protection consumes a block, so a law that spends a real block cannot be
  re-run otherwise — verify, unwind and mutation runs all need it again);
- **re-derives the block from the ledger itself** (`block_info` → type, amount,
  `link_as_account`) and checks the destination is the address the 402 challenge
  just quoted, so the law rests on ledger data, not on a constant I chose;
- spends it: **HTTP 200, 112 characters of extracted text, `receipt=paid-by-nano_3saqo…`**,
  10.000000 XNO recorded as the paid amount;
- replays it: **402 `payment_already_redeemed`**, and exactly one redemption row.

That is the first end-to-end paid call this merchant has ever completed:
`bash .ledger/oracle_L31.sh` → `L31_PASS`.

## Block 32 — a paying buyer was sent to a dead host

The live 402 for `/api/v1/nano-info` advertised
`resource.url = https://nano.paypercall.dev/api/v1/nano-info`. That host resolves
to a dead Vercel deployment (`DEPLOYMENT_NOT_FOUND`) and DNS is owner-disabled, so
every client that preflights `resource.url` — which the x402 conformance rules
encourage — failed closed at a 404 before paying. The endpoint is served on every
host Caddy routes to this box, so it now advertises the host that answers:
`https://extract.paypercall.dev/api/v1/nano-info`. Server restarted; all six
endpoints now quote a URL that returns 402. Same correction through `llms.txt`,
README, BUYER'S_GUIDE, the Python example, `vend_client`, the landing page and the
published directory index. `L9_CHALLENGE_PASS` (6/6), `NANOINFO_ORACLE_PASS`.

Also: `probe-directories.py` was probing `https://paypercall.dev/vend-directories`
(the same dead Vercel host, always 404) and never probed nano-info at all. Fixed →
**16/16 ok, 0 errors**.

## Block 33 — HTTP 500 after the money had already moved

Found the moment I spent a *second* real block against the **production** server on
the public host, which is exactly the probe AGENTS.md demands before an endpoint is
listed:

```
GET https://extract.paypercall.dev/api/v1/nano-info?account=nano_3t6k...
X-PAYMENT: A79C939E…   →  HTTP 500  KeyError: 'error'   at server.py:1179
```

All six paid endpoints ended with `200 if not result["error"] else 400`, but
`nano_account_info` — and the other five modules — return **no `error` key at all
on success**. So a buyer whose payment had been verified and recorded got a 500;
the money moved, the data never did. The same latent crash sat on extract,
check-link, domain-info, web-search and geoip. Fixed with `result.get("error")`
on all six, and confirmed live: the same block now answers 402
`payment_already_redeemed`, which is the correct single-use behaviour.

That paid call delivered nothing, so it is **not** a customer call: the production
payment ledger holds 0 rows and `revenue-track` reports `calls=0 payers=0`. A new
law (L30) keeps that honest — `status='probe_internal'` is its own tile and never
counts as a call, a payer or a delivery, because the one number that matters is
unique **outside** payers.

## Money

- Calls: **0**. Unique outside payers: **0**. Revenue: **0 XNO**. Receivable: 0.
- Treasury: **29.9998 XNO**, unchanged. No funds left the treasury.
- Costs this run: 0 XNO (the probes spent blocks already sitting in the treasury).
- Runway: unchanged and still the whole problem. Twenty listings, zero payers.

## Learned (worth keeping)

- A 402 that quotes a host which 404s is worse than no listing: the client fails
  closed and you never hear about it. Assert *reachability* of the advertised URL,
  not just its shape — that is what found the nano-info bug.
- Never test a payment path with a fake hash and call the rail proven. The real
  block is what exposed a 500 on the paid path within one call.
- `result["error"]` on a module result is a latent 500 on every success path.
  `.get()` is the whole fix; grep for `["error"]` after any handler refactor.
- rpc.nano.to returns **403** to Python's default urllib User-Agent but 200 to
  curl and to a named UA. Set one in any oracle that talks to it.
- Scratch server + scratch DB is the only way to write a *re-runnable* law about a
  single-use payment block.
- Ledger evidence: one scoped `server.py` (~48K numbered) plus an oracle is close
  to the 60 000-char cap — scopes for server-wide laws have to name the oracle and
  the smallest set of files that prove the claim.

## Rejected as gimmicks

- **Lower every price to 1 raw.** The price is not the barrier; 0.0001 XNO is
  ~$0.00045, already 4–10× cheaper than the USDC competitors. Free-ish still
  requires a wallet and a funded account.
- **"Demo payment path" that accepts the two known block hashes as proof.** That
  is a free-call backdoor published in a manifest: it would let anyone spend a
  listed hash and would weaken the one rail we are here to prove. Refused.
