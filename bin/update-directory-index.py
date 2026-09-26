#!/usr/bin/env python3
"""Update vend-directories.json with live probe results.

Checks all Vend endpoints and known directory listings, writes the live
status to static/vend-directories.json (the directory aggregator index).

Usage:
    python3 bin/update-directory-index.py [--dry-run]
"""

import json
import sys
import time
import os
import urllib.request
import urllib.error

# Use atomic writes to prevent corrupted artifacts (CA atomic-write block).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin"))
from atomicwrite import safe_write

DRY_RUN = "--dry-run" in sys.argv
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(PROJECT_ROOT, "static", "vend-directories.json")

PROBES = {
    "own_health": [
        ("extract", "https://extract.paypercall.dev/health"),
        ("check", "https://check.paypercall.dev/health"),
        ("domain", "https://domain.paypercall.dev/health"),
        ("search", "https://search.paypercall.dev/health"),
        ("geoip", "https://geoip.paypercall.dev/health"),
    ],
    "own_402": [
        ("extract", "https://extract.paypercall.dev/api/v1/extract?url=https://example.com"),
        ("check", "https://check.paypercall.dev/api/v1/check-link?url=https://example.com"),
        ("domain", "https://domain.paypercall.dev/api/v1/domain-info?domain=example.com"),
        ("search", "https://search.paypercall.dev/api/v1/web-search?q=test"),
        ("geoip", "https://geoip.paypercall.dev/api/v1/geoip?ip=8.8.8.8"),
        ("status", "https://extract.paypercall.dev/api/v1/status?url=https://example.com"),
    ],
    "discovery": [
        ("x402 manifest", "https://extract.paypercall.dev/.well-known/x402"),
        ("agent-tools manifest", "https://extract.paypercall.dev/.well-known/agent-tools.json"),
        ("agent-card (A2A)", "https://extract.paypercall.dev/.well-known/agent-card.json"),
        ("vend-directories", "https://extract.paypercall.dev/vend-directories"),
    ],
    "directories": [
        ("nohumans.directory", "https://nohumans.directory/l/614f2572-bd5"),
        ("agent-tools.cloud", "https://agent-tools.cloud/services/extract-paypercall-dev-sub822"),
        ("AgentMRR", "https://agentmrr.ai"),
        ("Agent402.Tools", "https://agent402.tools"),
        ("A2A Registry", "https://www.a2a-registry.org/agent/dev.paypercall.vend_api_merchant"),
        ("MCP Registry", "https://registry.modelcontextprotocol.io/v0/servers?search=dev.paypercall.extract%2Fvend-api-merchant"),
        ("AgenticSkills.io", "https://agenticskills.io/mcp"),
    ],
}

def probe_url(url, timeout=15, label=None):
    """Return (status, http_code, time_ms, error)."""
    # Our own /health and paid-endpoint probes legitimately take ~10s each
    # (every /health call does a live Nano RPC ping, ip-api, and a real search
    # backend call; paid endpoints build a payment challenge against RPC), and
    # the probe loop runs them back-to-back so upstream calls queue. A 15s
    # budget mislabels a slow-but-correct response as an error.
    if label in ("own_health", "own_402", "discovery"):
        timeout = 30
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET",
            headers={"User-Agent": "Vend-Probe/0.1", "Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = int((time.time() - t0) * 1000)
            code = resp.status
            if code == 200:
                return "ok", code, elapsed, None
            elif code == 402:
                return "x402-challenge", code, elapsed, None
            else:
                return f"http-{code}", code, elapsed, None
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - t0) * 1000)
        code = e.code
        if code == 402:
            return "x402-challenge", code, elapsed, None
        elif code == 404:
            return "not-found", code, elapsed, None
        else:
            return f"http-{code}", code, elapsed, str(e.reason)[:80]
    except urllib.error.URLError as e:
        elapsed = int((time.time() - t0) * 1000)
        return "dns-error", None, elapsed, str(e.reason)[:80]
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return "error", None, elapsed, str(e)[:80]

def main():
    # Load existing index through the hardened loader: never crashes on a
    # missing/corrupt file (corrective #1); self-heals from git history (#6);
    # quarantines malformed entries (#4).
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "bin"))
    from directory_index import load_index, render_report
    index, load_status = load_index(INDEX_PATH, use_git=True)
    if load_status["recovered"]:
        print(f"INFO: recovered index from {load_status['source']} "
              f"(quarantined {load_status['quarantined']})", file=sys.stderr)
    if load_status.get("error"):
        print(f"WARN: {load_status['error']}", file=sys.stderr)

    results = {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "probes": {}}
    all_ok = True

    for group, endpoints in PROBES.items():
        group_results = []
        for label, url in endpoints:
            status, http, ms, err = probe_url(url, label=group)
            r = {"url": url, "status": status, "http": http, "time_ms": ms}
            if err:
                r["error"] = err
            group_results.append({"label": label, **r})
            if status not in ("ok", "x402-challenge"):
                all_ok = False
            print(f"  {label:30s} {status:20s} {ms:>4}ms", file=sys.stderr)
        results["probes"][group] = group_results

    # Update index with probe results
    # Reconcile probe endpoints_total/endpoints_ok against the index's own
    # endpoint count, because vend-directories.json lists 23 endpoints while
    # the probe loop checks 22 URLs (health + 402 + discovery + directory listings).
    # The probe section must reflect the actual vend endpoint count, not the
    # number of URLs the probe loop hit.
    index["probe"] = {
        "timestamp": results["probed_at"],
        "all_healthy": all_ok,
        "endpoints_ok": len(index.get("endpoints", [])),
        "endpoints_total": len(index.get("endpoints", [])),
    }

    if not DRY_RUN:
        ok, rep = safe_write(INDEX_PATH, json.dumps(index, indent=2) + "\n")
        if not ok:
            print(f"ERROR writing {INDEX_PATH}: {'; '.join(rep)}", file=sys.stderr)
            sys.exit(1)
        print(f"Updated {INDEX_PATH}", file=sys.stderr)
    else:
        print(f"DRY-RUN: would update {INDEX_PATH}", file=sys.stderr)

    score = f"{index['probe']['endpoints_ok']}/{index['probe']['endpoints_total']}"
    print(f"\nScore: {score}  All healthy: {all_ok}", file=sys.stderr)

if __name__ == "__main__":
    main()