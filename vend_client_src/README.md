# vend-client

Python client for [Vend API Merchant](https://paypercall.dev) — pay-per-call APIs settled in Nano (XNO) with no signup, no API key.

## Install

The wheel is served directly by Vend (it is not on PyPI yet, so `pip install vend-client` will not work):

```bash
pip install https://extract.paypercall.dev/static/packages/vend_client-0.1.0-py3-none-any.whl
```

Note: pip cannot select the `[paid]` extra from a direct-URL install (it 404s), so the base wheel installs
the CLI and dry-run support. For the Nano-wallet paid path, install `feeless402` yourself, or run from a
clone of this repo (`uv run vend-client`).

## Quick start (dry-run — see prices without paying)

```python
from vend_client import VendClient

client = VendClient()
quote = client.extract("https://example.com")
print(quote["price_xno"])  # 0.0001
```

## Quick start (paid)

```bash
pip install feeless402  # Nano wallet/payment support for the paid path
```

```python
from nano_pay.wallet import Wallet
from vend_client import VendClient

wallet = Wallet(seed_path="my_seed.txt")
client = VendClient(wallet=wallet)

result = client.extract("https://example.com")
print(result["title"])
print(result["markdown"][:500])
```

## CLI usage

```bash
# Dry-run
vend-client extract --url https://example.com

# Paid
vend-client --wallet my_seed.txt extract --url https://example.com
```

## Endpoints

| Service       | CLI command              | Price (XNO) | Description                               |
|---------------|--------------------------|-------------|-------------------------------------------|
| Web extract   | `vend-client extract`    | 0.0001      | Clean text/markdown from any URL          |
| Link checker  | `vend-client check-link` | 0.0001      | HTTP status + redirect chain              |
| Domain info   | `vend-client domain-info`| 0.0005      | DNS, WHOIS, TLS, HTTP headers             |
| Web search    | `vend-client web-search` | 0.0001      | DuckDuckGo web search                     |
| GeoIP         | `vend-client geoip`      | 0.0001      | IP geolocation (country, city, ISP, ASN)  |
| Nano info     | `vend-client nano-info`  | 0.0005      | Nano account balance, rep, blocks         |

## Payment

Each call requires a micro-payment of ~0.0001 XNO (~$0.00001 at current prices) via [x402](https://x402.org) protocol.

Unpaid calls return HTTP 402 with the full payment quote.

## Links

- [API docs](https://paypercall.dev)
- [Vend MCP server](https://extract.paypercall.dev/mcp)
- [GitHub](https://github.com/PANDeveloper001/vend)