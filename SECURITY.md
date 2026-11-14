# Security

## Reporting a vulnerability

Report it privately through GitHub: **Security -> Report a vulnerability** on
https://github.com/dhyabi2/vend (private vulnerability reporting). Please do not open a public issue for
something that lets a caller get a paid result without paying, take a payment without a result, or reach
anything other than the public web through an endpoint that fetches URLs.

Include the request, the response and, where money moved, the block hash.

## What the service holds

- The server is receive-only. It holds no seed and no private key and cannot send funds.
- A payment is checked on the Nano ledger: the amount and the receiving account must match the
  challenge, a send the ledger reports as unconfirmed is refused, and each block hash is redeemable once.
- No signup and no API key exist, so there are no credentials of yours to leak.
