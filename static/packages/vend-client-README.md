# vend-client — Python client for Vend API Merchant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pay-per-call APIs settled in Nano (XNO). No signup, no API key.**

`vend-client` wraps all 6 Vend endpoints (extract, check-link, domain-info, web-search, geoip, nano-info) with x402 payment support. Use it from your Python code or from the command line.

---

## Quick start

```bash
# Install
pip install vend-client

# Dry-run — see what a call would cost
vend-client extract --url https://example.com

# Paid call (with a Nano wallet)
vend-client --wallet /path/to/seed.txt extract --url https://example.com
```

## Python API

```python
from vend_client import VendClient

# Dry-run (read prices without paying)
client = VendClient()
result = client.extract("https://example.com")
print(result["price_xno"], "XNO")  # 0.0001

# Paid call (with wallet)
from nano_pay.wallet import Wallet
wallet = Wallet(seed_path="/path/to/seed.txt")
client = VendClient(wallet=wallet)
result = client.domain_info("example.com")
```

## Endpoints

| Service | Price (XNO) | Description |
|---------|-------------|-------------|
| extract | 0.0001 | Clean text/markdown from any URL |
| check-link | 0.0001 | HTTP status, redirect chain |
| domain-info | 0.0005 | DNS, WHOIS, TLS cert, headers |
| web-search | 0.0001 | DuckDuckGo web search |
| geoip | 0.0001 | IP geolocation |
| nano-info | 0.0005 | Nano account intelligence |

## License

MIT