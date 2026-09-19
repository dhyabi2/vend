#!/usr/bin/env python3
"""Build the Nano × x402 directory aggregator.

Scans the public x402 indexes (Agent402.Tools, the CDP x402 Bazaar) for
sellers that advertise `nano:mainnet` settlement, merges in Vend's own
endpoints as the always-included reference, probes the live x402 manifest of
the known Nano sellers for their actual Nano accepts, and writes
`static/nano-directory.json` plus `static/nano-directory.html`.

The output is served by the Vend server at `/nano-directory` (JSON) and
`/nano-services` (HTML). It is a public, machine-readable registry of
"Nano-settled x402 services" — the exact index the Nano ecosystem lacks.

Usage:
    python3 bin/build-nano-directory.py [--dry-run]
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

# Use atomic writes to prevent corrupted artifacts (CA atomic-write block).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin"))
from atomicwrite import safe_write

DRY_RUN = "--dry-run" in sys.argv
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(PROJECT_ROOT, "static", "nano-directory.json")
OUT_HTML = os.path.join(PROJECT_ROOT, "static", "nano-directory.html")

UA = {"User-Agent": "Vend-NanoDirectory/0.1 (nano-settlement registry; vend@paypercall.dev)"}

# Vend's own five endpoints, always listed (they are the canonical set).
VEND_ENDPOINTS = [
    {"name": "extract", "origin": "https://extract.paypercall.dev",
     "url": "https://extract.paypercall.dev/api/v1/extract",
     "description": "Extract clean text/markdown from a URL", "price_xno": 0.0001},
    {"name": "check-link", "origin": "https://check.paypercall.dev",
     "url": "https://check.paypercall.dev/api/v1/check-link",
     "description": "Check HTTP status, response time, redirect chain", "price_xno": 0.0001},
    {"name": "domain-info", "origin": "https://domain.paypercall.dev",
     "url": "https://domain.paypercall.dev/api/v1/domain-info",
     "description": "DNS, WHOIS, SSL, HTTP headers intelligence", "price_xno": 0.0005},
    {"name": "web-search", "origin": "https://search.paypercall.dev",
     "url": "https://search.paypercall.dev/api/v1/web-search",
     "description": "Web search via DuckDuckGo — titles, URLs, snippets", "price_xno": 0.0001},
    {"name": "geoip", "origin": "https://geoip.paypercall.dev",
     "url": "https://geoip.paypercall.dev/api/v1/geoip",
     "description": "IP geolocation: country, city, ISP, ASN, timezone", "price_xno": 0.0001},
]


def fetch_json(url, timeout=30):
    """Fetch a JSON document with a short timeout. Returns dict/list or None."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # any fetch failure is a skip, not a crash
        print(f"    ! fetch failed {url}: {e}", file=sys.stderr)
        return None


def is_nano_network(network, asset=None):
    """A network/asset pair advertises Nano settlement if the CAIP-2 id says
    nano OR the asset token is XNO (case-insensitive)."""
    n = (network or "").lower()
    a = (asset or "").lower()
    return "nano" in n or a in ("xno", "nano")


def scan_agent402(max_pages=44):
    """Walk Agent402.Tools's cross-seller index for nano:mainnet sellers."""
    found = []
    for page in range(max_pages):
        url = f"https://agent402.tools/api/index?page={page}&perPage=100"
        data = fetch_json(url)
        if not data:
            break
        sellers = data.get("sellers", [])
        if not sellers:
            break
        for s in sellers:
            nets = s.get("networks") or []
            if any(n in ("nano:mainnet", "nano") for n in nets):
                found.append(s)
    return found


def scan_bazaar(max_pages=20):
    """Walk the CDP x402 Bazaar resource index for XNO accepts."""
    found = {}
    offset = 0
    for _ in range(max_pages):
        url = f"https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=1000&offset={offset}"
        data = fetch_json(url, timeout=45)
        if not data:
            break
        resources = data.get("resources") or []
        if not resources:
            break
        for r in resources:
            accepts = r.get("accepts", []) or []
            for a in accepts:
                if is_nano_network(a.get("network"), a.get("asset")):
                    origin = (r.get("url") or "").split("/")[0]
                    origin = origin.replace("https://", "").replace("http://", "")
                    found.setdefault(origin, {
                        "origin": origin or r.get("url"),
                        "resource": r.get("url"),
                        "accepts": [],
                    })["accepts"].append(a)
        total = data.get("pagination", {}).get("total", 0)
        offset += len(resources)
        if offset >= total:
            break
    return list(found.values())


def probe_nano_manifest(origin):
    """Fetch <origin>/.well-known/x402 and pull the Nano accepts.

    Handles both the standard shape (resources is a list of objects each with
    an ``accepts`` array) and non-standard shapes (resources is a list of
    path strings, payment declared in a top-level ``payment``/``payments``
    block, as some experimental sellers emit). Any origin whose manifest
    carries a Nano accepts anywhere is reported with its Nano resources.
    """
    base = origin if origin.startswith("http") else f"https://{origin}"
    data = fetch_json(f"{base}/.well-known/x402", timeout=20)
    if not data:
        return None, []
    resources = data.get("resources", []) or []
    if not isinstance(resources, list):
        resources = []
    nano_resources = []
    extra_nano = False
    for r in resources:
        if not isinstance(r, dict):
            continue  # path-string form; payment is in the top-level block
        accepts = r.get("accepts", []) or []
        if not isinstance(accepts, list):
            accepts = []
        nano_accepts = [a for a in accepts if isinstance(a, dict)
                        and is_nano_network(a.get("network"), a.get("asset"))]
        url = r.get("url") or r.get("resource") or ""
        if nano_accepts:
            nano_resources.append({"url": url, "accepts": nano_accepts})
    # Top-level payment block(s) may declare Nano even when resources are paths.
    for key in ("payment", "payments", "assets", "networks"):
        block = data.get(key)
        if isinstance(block, dict) and is_nano_network(block.get("network"), block.get("asset")):
            extra_nano = True
        elif isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and is_nano_network(item.get("network"), item.get("asset")):
                    extra_nano = True
    if extra_nano and not nano_resources:
        nano_resources.append({"url": "", "accepts": [], "note": "Nano declared in top-level payment block"})
    return data, nano_resources


def main():
    print("Building Nano x402 directory aggregate ...", file=sys.stderr)
    t0 = time.time()

    # 1. Vend's own endpoints (canonical)
    vend_rows = [{"name": e["name"], "origin": e["origin"], "url": e["url"],
                  "description": e["description"], "price_xno": e["price_xno"],
                  "source": "vend", "advertised_networks": ["nano:mainnet"]}
                 for e in VEND_ENDPOINTS]

    # 2. Agent402.Tools scan
    print("Scanning Agent402.Tools index (44 pages) ...", file=sys.stderr)
    a402 = scan_agent402()
    for s in a402:
        origin = (s.get("origin") or "").replace("https://", "").replace("http://", "")
        vend_rows.append({"name": s.get("displayName", origin), "origin": origin,
                          "homepage": s.get("homepage"),
                          "tool_count": s.get("toolCount"),
                          "advertised_networks": s.get("networks"),
                          "source": "agent402"})
    print(f"  Agent402.Tools: {len(a402)} nano sellers", file=sys.stderr)

    # 3. CDP Bazaar scan (for independent confirmation)
    print("Scanning CDP x402 Bazaar for XNO accepts ...", file=sys.stderr)
    bazaar = scan_bazaar()
    bazaar_origins = {b["origin"] for b in bazaar}
    print(f"  Bazaar: {len(bazaar)} origins with XNO accepts", file=sys.stderr)
    for b in bazaar:
        if b["origin"] not in {r["origin"] for r in vend_rows}:
            vend_rows.append({"name": b["origin"], "origin": b["origin"],
                              "resource": b.get("resource"),
                              "source": "cdp-bazaar",
                              "advertised_networks": ["nano:mainnet"]})

    # 4. Probe live x402 manifests for each distinct Nano origin
    origins = {}
    for r in vend_rows:
        o = r["origin"].replace("https://", "").replace("http://", "")
        origins.setdefault(o, r)
    print(f"Probing {len(origins)} distinct Nano origins' x402 manifests ...", file=sys.stderr)
    manifest_data = {}
    for o in list(origins):
        data, nano_res = probe_nano_manifest(o)
        if data is not None:
            manifest_data[o] = {"manifest_present": True,
                                "manifest_name": data.get("name"),
                                "manifest_seller": data.get("seller"),
                                "nano_resources": nano_res}
        else:
            manifest_data[o] = {"manifest_present": False, "nano_resources": []}
        origins[o]["manifest"] = manifest_data[o]

    # 5. Build the output index
    index = {
        "name": "Nano × x402 Directory",
        "description": "Public registry of pay-per-call services that settle in Nano (XNO) via x402. "
                       "Compiled by Vend from the public x402 indexes; every origin has an advertised "
                       "nano:mainnet settlement rail.",
        "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "probed": True,
        "sources": {
            "agent402.tools": "https://agent402.tools/api/index",
            "cdp-bazaar": "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources",
        },
        "services": list(origins.values()),
        "tallies": {
            "distinct_origins": len(origins),
            "vend_endpoints": len(VEND_ENDPOINTS),
            "third_party_nano_sellers": len(origins) - len(VEND_ENDPOINTS),
            "agent402_sellers": len(a402),
            "bazaar_origins": len(bazaar_origins),
        },
    }

    # 6. Write JSON (atomic temp-replace — no partial artifacts)
    ok, rep = safe_write(OUT_JSON, json.dumps(index, indent=2) + "\n")
    if not ok:
        print(f"ERROR writing {OUT_JSON}: {'; '.join(rep)}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {OUT_JSON} ({len(origins)} origins)", file=sys.stderr)

    # 7. Write HTML (simple, dependency-free, dark theme matching landing page)
    rows_html = []
    for r in origins.values():
        mn = r.get("manifest", {})
        nets = ", ".join(r.get("advertised_networks") or [])
        src = {
            "vend": "Vend (self)",
            "agent402": "Agent402.Tools index",
            "cdp-bazaar": "CDP Bazaar",
        }.get(r.get("source"), r.get("source"))
        manifest_badge = "manifest ✓" if mn.get("manifest_present") else "no manifest"
        rows_html.append(
            f"<div class='row'><div class='name'>{r['name']}</div>"
            f"<div class='origin'>{r['origin']}</div>"
            f"<div class='src'>{src}</div>"
            f"<div class='nets'>{nets}</div>"
            f"<div class='badge'>{manifest_badge}</div></div>"
        )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nano × x402 Directory</title>
<meta name="description" content="Public registry of pay-per-call services that settle in Nano (XNO) via x402.">
<style>
body{{font-family:ui-monospace,monospace;background:#0d1117;color:#c9d1d9;max-width:900px;margin:2rem auto;padding:0 1rem}}
h1{{color:#58a6ff}} a{{color:#58a6ff;text-decoration:none}}
.row{{display:grid;grid-template-columns:1.2fr 1.6fr .8fr 1.2fr auto;gap:.5rem;padding:.5rem 0;border-bottom:1px solid #21262d;align-items:baseline}}
.name{{font-weight:bold;color:#e6edf3}} .origin{{color:#8b949e;font-size:.9em}}
.src{{font-size:.85em;color:#7ee787}} .nets{{font-size:.85em;color:#d2a8ff}}
.badge{{font-size:.8em;color:#f0883e}}
.meta{{color:#8b949e;font-size:.9em;margin:1rem 0}}
</style></head><body>
<h1>Nano × x402 Directory</h1>
<p class="meta">Pay-per-call services that settle in Nano (XNO) via x402 — compiled by
<a href="https://paypercall.dev">Vend</a> from the public x402 indexes.
Machine-readable: <a href="/nano-directory">nano-directory.json</a> · compiled {index['compiled_at']} ·
{index['tallies']['distinct_origins']} distinct origins.</p>
{''.join(rows_html)}
<p class="meta">All origins advertise a <code>nano:mainnet</code> settlement rail. Compiled by an
autonomous AI agent (Vend) — verify a live price against each origin's own x402 challenge before paying.</p>
</body></html>
"""
    ok, rep = safe_write(OUT_HTML, html)
    if not ok:
        print(f"ERROR writing {OUT_HTML}: {'; '.join(rep)}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {OUT_HTML}", file=sys.stderr)
    print(f"\nDone in {time.time() - t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()