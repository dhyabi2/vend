# Vend: pricing, privacy, refunds and payment risks

Vend is a hosted pay-per-call API at `https://extract.paypercall.dev` (MCP: `https://extract.paypercall.dev/mcp`).
It is built and operated by the maintainer of this repository, [@dhyabi2](https://github.com/dhyabi2), and this
repository is its complete source (MIT). Everything below can be checked against the code.

## Pricing

- Each call has a fixed price in Nano (XNO), between 0.0001 and 0.0005 XNO. The authoritative list is the
  machine-readable manifest at `https://extract.paypercall.dev/.well-known/x402`; the unpaid call to any
  endpoint answers HTTP 402 with the exact amount and the account to pay.
- Five free calls per caller per rolling day, with no signup. After that a call needs a payment. The browser
  agent is the exception: it has no free calls.
- There is no subscription, no account and no minimum. Nano has no network fee, so the price is the whole cost.

## Privacy

- No signup, no API key, no cookie, no tracking script. Vend never asks for an email, a name or a wallet seed.
- The free-trial counter lives in memory only, keyed by network prefix, and is cleared when the service restarts
  (`trial_tracker.py`).
- For a paid call Vend stores the block hash, the amount, the sending Nano account, the endpoint and the
  delivery status (`store.py`). These are the facts already public on the Nano ledger, plus which endpoint was
  bought. The result of the call is not stored.
- The web server keeps a rolling access log (client address, path and query string, status) for operations and
  abuse handling, capped at about 100 MB. A URL or search term you send is therefore in that log until it rolls.
- Endpoints that fetch a page or run a search send your URL or query to that site or search provider, as any
  fetch would. Nothing is sold or shared beyond that.
- A Nano payment is public and permanent on the ledger: anyone can see that your account paid Vend's account.

## Refunds and failed calls

- A request that cannot be served because a required parameter is missing is refused **before** any payment is
  taken; the 400 carries `payment_taken: false`.
- If the paid work fails, it is retried once. If it fails again the call answers 502 and the block is recorded
  as `failed`; `GET /api/v1/delivery-proof?block_hash=...` shows what a payment delivered.
- A block hash pays for one call. Presenting it again is refused.
- **Browser agent runs** (`/api/v1/browser-agent`, where offered) are never free and cost more than the other
  calls, so a failure on our side is made good with another run: if a paid run fails, or could not start, call
  again with `retry_of=<job_id>` and a new run starts with no new payment. One payment buys at most three runs
  this way, a job can be retried once, and only the job id you were given unlocks it. A run that finished, or
  that used up its step or time budget, did its work and is not retried. If the agent is down when you call,
  the answer is 503 and nothing is taken.
- **There is no automatic refund.** The server is receive-only: it holds no key and cannot send. To dispute a
  payment, open an issue at https://github.com/dhyabi2/vend/issues with the block hash; the record above shows
  whether it was delivered.

## Nano wallet and transaction risks

- A Nano send is final. It cannot be reversed by you, by Vend or by anyone else.
- Pay the account and the exact amount named in the 402 challenge of the call you are making, never an address
  copied from a document or a listing. A payment to another account, or of another amount, is not matched to
  your call.
- Wait for your send to be confirmed before retrying; an unconfirmed send is refused.
- Keep your seed and private key in your own wallet. Vend never needs them and no Vend endpoint accepts one.
- XNO's price against other currencies moves; prices here are fixed in XNO.

## Security

See [SECURITY.md](SECURITY.md) for how to report a vulnerability privately.
