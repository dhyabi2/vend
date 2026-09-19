"""VendClient — call Vend API Merchant endpoints via x402.

Usage:
    client = VendClient()                          # dry-run (read prices)
    client = VendClient(wallet=wallet)              # pay with a nano_pay wallet
    result = client.extract("https://example.com")
    result = client.check_link("https://example.com")
    result = client.domain_info("example.com")
    result = client.web_search("search query")
    result = client.geoip("8.8.8.8")
    result = client.nano_info("nano_1...")

CLI:
    vend-client extract --url https://example.com
    vend-client check-link --url https://example.com
    vend-client domain-info --domain example.com
    vend-client web-search --q "search query"
    vend-client geoip --ip 8.8.8.8
    vend-client nano-info --account nano_1...
"""

import json
import os
import sys
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from nano_pay.x402 import request_with_payment, parse_quote
    from nano_pay.wallet import Wallet
except ImportError:
    request_with_payment = None  # type: ignore
    parse_quote = None  # type: ignore
    Wallet = None  # type: ignore


class VendError(Exception):
    """Raised when a Vend API call fails."""


# Default endpoints — can be overridden via env vars for self-hosting or testing
DEFAULT_ENDPOINTS = {
    "extract": "https://extract.paypercall.dev/api/v1/extract",
    "check_link": "https://check.paypercall.dev/api/v1/check-link",
    "domain_info": "https://domain.paypercall.dev/api/v1/domain-info",
    "web_search": "https://search.paypercall.dev/api/v1/web-search",
    "geoip": "https://geoip.paypercall.dev/api/v1/geoip",
    "nano_info": "https://extract.paypercall.dev/api/v1/nano-info",
}


class VendClient:
    """Client for Vend's pay-per-call APIs.

    Args:
        wallet: A nano_pay Wallet instance. If None, the client runs in dry-run
            mode: it fetches the 402 challenge to show prices, but cannot pay.
        endpoints: Optional dict mapping service names to base URLs.
            Defaults to the live Vend endpoints.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        wallet: Optional["Wallet"] = None,
        endpoints: Optional[dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        if httpx is None:
            raise VendError("httpx is required: pip install vend-client[cli]")

        self._wallet = wallet
        self._endpoints = endpoints or dict(DEFAULT_ENDPOINTS)
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout, follow_redirects=False)

    # --- Convenience properties (readable from dry-run or paid) ---

    def _call(self, service: str, params: dict[str, str]) -> dict:
        """Call a Vend endpoint with optional x402 payment."""
        url = self._endpoints.get(service)
        if not url:
            raise VendError(f"Unknown service: {service}")

        if self._wallet is not None and request_with_payment is not None:
            # Paid call — use nano_pay's x402 flow
            try:
                result = request_with_payment(
                    url,
                    params=params,
                    wallet=self._wallet,
                    client=self._client,
                )
                if isinstance(result, dict):
                    return result
                return json.loads(result)
            except Exception as e:
                raise VendError(f"Paid call to {service} failed: {e}") from e
        else:
            # Dry-run: get the 402 quote to see the price
            resp = self._client.get(url, params=params)
            if resp.status_code == 402:
                quote = self._parse_402_body(resp)
                quote["_dry_run"] = True
                return quote
            if resp.status_code == 200:
                return resp.json()
            raise VendError(
                f"{service} returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

    @staticmethod
    def _parse_402_body(resp) -> dict:
        """Extract payment info from a 402 response body."""
        try:
            return resp.json()
        except Exception:
            return {"error": "payment_required", "raw_body": resp.text[:500]}

    # --- Per-endpoint methods ---

    def extract(self, url: str) -> dict:
        """Extract clean text/markdown from a URL."""
        return self._call("extract", {"url": url})

    def check_link(self, url: str) -> dict:
        """Check HTTP status, response time, redirect chain for a URL."""
        return self._call("check_link", {"url": url})

    def domain_info(self, domain: str) -> dict:
        """Full domain intelligence: DNS, WHOIS, TLS, HTTP headers."""
        return self._call("domain_info", {"domain": domain})

    def web_search(self, q: str) -> dict:
        """Web search via DuckDuckGo."""
        return self._call("web_search", {"q": q})

    def geoip(self, ip: str) -> dict:
        """IP geolocation."""
        return self._call("geoip", {"ip": ip})

    def nano_info(self, account: str) -> dict:
        """Nano account intelligence: balance, rep, blocks."""
        return self._call("nano_info", {"account": account})

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    """CLI entry point: vend-client <service> [--param value]"""
    import argparse

    parser = argparse.ArgumentParser(
        description="vend-client: call Vend API Merchant from the command line"
    )
    parser.add_argument("--wallet", help="Path to nano_pay wallet seed file")

    subparsers = parser.add_subparsers(dest="service", required=True)

    for service, param_name in [
        ("extract", "url"),
        ("check-link", "url"),
        ("domain-info", "domain"),
        ("web-search", "q"),
        ("geoip", "ip"),
        ("nano-info", "account"),
    ]:
        sp = subparsers.add_parser(service, help=f"Call {service} endpoint")
        sp.add_argument(f"--{param_name}", required=True, help=param_name)

    args = parser.parse_args()

    # Map CLI service names to method names
    service_map = {
        "extract": "extract",
        "check-link": "check_link",
        "domain-info": "domain_info",
        "web-search": "web_search",
        "geoip": "geoip",
        "nano-info": "nano_info",
    }
    param_map = {
        "extract": "url",
        "check-link": "url",
        "domain-info": "domain",
        "web-search": "q",
        "geoip": "ip",
        "nano-info": "account",
    }

    wallet = None
    if args.wallet and Wallet is not None and request_with_payment is not None:
        wallet = Wallet(seed_path=args.wallet)

    service_name = args.service
    method_name = service_map[service_name]
    param_name = param_map[service_name]
    param_value = getattr(args, param_name)

    client = VendClient(wallet=wallet)
    try:
        result = getattr(client, method_name)(param_value)
    except VendError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    finally:
        client.close()

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()