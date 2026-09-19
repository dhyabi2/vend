#!/usr/bin/env python3
"""Probe all Vend endpoints and directory listings, report live status.

Usage:
    python3 bin/probe-directories.py [--verbose]
    
Scans:
- All 5 Vendor endpoints (/health and /api/v1/extract unpaid)
- nohumans.directory listing page
- agent-tools.cloud listing
- AgentMRR
- agent402.tools index
- x402-list.com (if 7-day window expired)
Output: JSON to stdout, optionally verbose to stderr.
"""

import json
import sys
import time
import urllib.request
import urllib.error
import os

VERBOSE = "--verbose" in sys.argv

PROBES = [
    # Own endpoints - health
    ("extract health", "https://extract.paypercall.dev/health", None),
    ("check health", "https://check.paypercall.dev/health", None),
    ("domain health", "https://domain.paypercall.dev/health", None),
    ("search health", "https://search.paypercall.dev/health", None),
    ("geoip health", "https://geoip.paypercall.dev/health", None),
    # Own endpoints - unpaid (should return 402)
    ("extract 402", "https://extract.paypercall.dev/api/v1/extract?url=https://example.com", None),
    ("check 402", "https://check.paypercall.dev/api/v1/check-link?url=https://example.com", None),
    ("domain 402", "https://domain.paypercall.dev/api/v1/domain-info?domain=example.com", None),
    ("search 402", "https://search.paypercall.dev/api/v1/web-search?q=test", None),
    ("geoip 402", "https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8", None),
    ("nano-info 402", "https://extract.paypercall.dev/api/v1/nano-info?account=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3", None),
    # Discovery endpoints
    ("x402 manifest", "https://extract.paypercall.dev/.well-known/x402", None),
    ("agent-tools manifest", "https://extract.paypercall.dev/.well-known/agent-tools.json", None),
    # Third-party directories
    ("nohumans listing", "https://nohumans.directory/l/614f2572-bd5", None),
    ("agent-tools.cloud listing", "https://agent-tools.cloud/services/extract-paypercall-dev-sub822", None),
    # The directory index is served by the API app, on the host that
    # actually answers; paypercall.dev itself is a switched-off Vercel
    # deployment (owner-disabled), so probing it there always 404s.
    ("vend-directories", "https://extract.paypercall.dev/vend-directories", None),
]

def probe(label, url, expected_status=None):
    """Try to fetch URL and return status info."""
    result = {"label": label, "url": url, "status": "unknown", "http": None, "time_ms": None, "error": None}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Vend-Probe/0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result["time_ms"] = int((time.time() - t0) * 1000)
            result["http"] = resp.status
            body = resp.read(500)
            if resp.status == 200:
                result["status"] = "ok"
            elif resp.status == 402:
                result["status"] = "x402-challenge"
            else:
                result["status"] = f"http-{resp.status}"
    except urllib.error.HTTPError as e:
        result["time_ms"] = int((time.time() - t0) * 1000)
        result["http"] = e.code
        if e.code == 402:
            body = e.read(500)
            result["status"] = "x402-challenge"
        elif e.code == 404:
            result["status"] = "not-found"
        else:
            result["status"] = f"http-{e.code}"
    except Exception as e:
        result["time_ms"] = int((time.time() - t0) * 1000)
        result["error"] = str(e)[:100]
        result["status"] = "error"
    
    if VERBOSE:
        print(f"  {label:30s} {result['status']:20s} {result.get('time_ms', '?'):>5}ms", file=sys.stderr)
    return result

def main():
    results = []
    errors = 0
    
    print(f"Probing {len(PROBES)} endpoints...", file=sys.stderr if VERBOSE else sys.stderr)
    
    for label, url, expected in PROBES:
        r = probe(label, url, expected)
        results.append(r)
        if r["status"] in ("error", "not-found"):
            errors += 1
    
    # Summary
    ok_count = sum(1 for r in results if r["status"] in ("ok", "x402-challenge"))
    
    print(json.dumps({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(results),
        "ok": ok_count,
        "errors": errors,
        "results": results,
        "score": f"{ok_count}/{len(results)}"
    }, indent=2))

if __name__ == "__main__":
    main()