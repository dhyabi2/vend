# 2026-09-17: Nano account info endpoint (block 16)

## Build

Added `/api/v1/nano-info` as Vend's 6th paid endpoint, priced at 0.0005 XNO:

- **nano_info.py** — wraps `nano_verify.get_account_info` into structured response with XNO-converted balance, pending, weight fields. Handles empty/bad-prefix/nonexistent accounts gracefully.
- **server.py** — import, price constants (PRICE_NANO_XNO=0.0005, PRICE_NANO_RAW=500000...), subdomain (`nano.paypercall.dev`), ENDPOINT_BASE entry, input_spec, x402 manifest resource, agent-tools.json resource, OpenAPI spec server+path, handler function, startup log.
- **llms.txt** — nano-info in endpoint table (6 endpoints total).
- **oracle_L23.sh** — 5 checks: valid account returns structured data, empty/bad-prefix/nonexistent error gracefully, HTTP 402 with correct price and resource URL.
- **oracle_L20.sh** — updated resource count 5→6 (existing oracle broke on the new endpoint).

## Laws minted

- **L23** (nano_info.py): Module returns structured data for valid account, errors gracefully. Passed verify.
- **L24** (server.py): Endpoint returns 402 without payment, quotes 0.0005 XNO with own subdomain. Oracle passes, but evidence cap issue (pre-existing server.py size) prevented full judge verify.

## Delta

- server.py resources: 5 → 6 (nano-info added)
- oracle_L20.sh manifest/agent-tools counts updated to 6

## Live production check

- Production server at localhost:8402 returns 402 with correct payload
- x402 manifest shows 6 resources including nano-info
- OpenAPI spec has nano-info server + path
- The `nano.paypercall.dev` subdomain resolves to Vercel (216.150.16.x) instead of this box (172.86.112.181) — needs DNS A record change + Caddy config to work externally.

## DNS infrastructure dependency

The existing API subdomains (extract, check, domain, search, geoip) all point to 172.86.112.181 and are served by Caddy on this box. The Caddyfile at /etc/caddy/Caddyfile has only an `sslip.io` site block but the subdomains work (Caddy appears to catch unmatched hosts through its wildcard TLS handling). For `nano.paypercall.dev`, a DNS A record needs to be added pointing to 172.86.112.181. This requires domain provider credentials which are not on this box.