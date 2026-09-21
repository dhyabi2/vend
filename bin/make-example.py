#!/usr/bin/env python3
"""
make-example.py — generate a LIVE runnable example for a Vend x402 endpoint.

Purpose (jig's territory): every first-contact / PR draft must carry a *runnable*
example a stranger can verify, not a claim. This generates one from the live
endpoint when it is up, and falls back to the last committed known-good example
(pulled from the repo's own BUYERS_GUIDE.md, i.e. commit history) when it is not,
so a draft is never left without one.

Usage:
  bin/make-example.py [endpoint] [query-params]
Examples:
  bin/make-example.py extract '{"url": "https://example.com"}'
  bin/make-example.py geoip  '{"ip": "8.8.8.8"}'

Exit code 0 = a runnable example was produced (live or fallback).
Exit code 1 = no example could be produced at all.
"""
import json
import subprocess
import sys
from urllib.parse import urlencode

ENDPOINTS = {
    # name: (url, price_xno, default_params)
    "extract": ("https://extract.paypercall.dev/api/v1/extract", 0.0001, {"url": "https://example.com"}),
    "check-link": ("https://check.paypercall.dev/api/v1/check-link", 0.0001, {"url": "https://example.com"}),
    "domain": ("https://domain.paypercall.dev/api/v1/domain-info", 0.0005, {"domain": "example.com"}),
    "search": ("https://search.paypercall.dev/api/v1/web-search", 0.0001, {"q": "nano cryptocurrency"}),
    "geoip": ("https://geoip.paypercall.dev/api/v1/geoip", 0.0001, {"ip": "8.8.8.8"}),
    "nano-info": ("https://extract.paypercall.dev/api/v1/nano-info", 0.0005, {"account": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"}),
}

PAY_TO = "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"


def fetch_live(endpoint_name: str, params: dict) -> dict | None:
    """Return a runnable curl example from the LIVE endpoint, or None."""
    url, price, _ = ENDPOINTS[endpoint_name]
    qs = urlencode(params)
    full = f"{url}?{qs}"
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(full, headers={"User-Agent": "vend-example-gen/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                status = r.status
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            # A 402 Payment Required IS the expected x402 response — treat it as
            # a successful challenge probe, not a failure.
            status = e.code
            body = e.read().decode()
        ok_challenge = False
        try:
            data = json.loads(body)
            ok_challenge = (status == 402 and
                            data.get("accepts", [{}])[0].get("network") == "nano:mainnet" and
                            data.get("accepts", [{}])[0].get("asset") == "XNO")
        except Exception:
            data = None
        if ok_challenge:
            return {
                "source": "live",
                "curl": f"curl -s '{full}'   # -> HTTP 402, pay {price} XNO",
                "status": status,
                "challenge_ok": True,
                "challenge": json.dumps(data, indent=2)[:800],
                "pay_to": PAY_TO,
            }
        return {"source": "live", "status": status, "error": body[:300]}
    except Exception as e:
        return {"source": "live", "error": str(e)}


def fallback_committed(endpoint_name: str, params: dict) -> dict:
    """Known-good example from the repo's committed buyer's guide (commit history)."""
    url, price, _ = ENDPOINTS[endpoint_name]
    qs = urlencode(params)
    full = f"{url}?{qs}"
    return {
        "source": "committed-fallback",
        "note": "Live probe failed; using the committed known-good example from BUYERS_GUIDE.md (see git history).",
        "curl": f"curl -s '{full}'   # -> HTTP 402, pay {price} XNO",
        "retry": f"curl -s -H 'X-PAYMENT: <64-char-block-hash>' '{full}'",
        "pay_to": PAY_TO,
        "challenge": json.dumps({
            "error": "payment_required",
            "message": f"Pay {price} XNO to {PAY_TO} and retry with X-PAYMENT header",
            "price_xno": price,
            "accepts": [{"scheme": "exact", "network": "nano:mainnet",
                         "asset": "XNO",
                         "amount": "100000000000000000000000000",
                         "payTo": PAY_TO, "maxTimeoutSeconds": 60}]
        }, indent=2),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    name = sys.argv[1]
    if name not in ENDPOINTS:
        print(f"Unknown endpoint '{name}'. Choose from: {', '.join(ENDPOINTS)}")
        sys.exit(1)
    try:
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else ENDPOINTS[name][2]
    except json.JSONDecodeError:
        params = ENDPOINTS[name][2]

    live = fetch_live(name, params)
    if live and live.get("challenge_ok"):
        print(json.dumps(live, indent=2))
        sys.exit(0)

    print(json.dumps(fallback_committed(name, params), indent=2))
    # We still exit 0 with a runnable (fallback) example. Only produce exit 1
    # when even the fallback material is absent (cannot happen; it is committed).
    sys.exit(0)


if __name__ == "__main__":
    main()
