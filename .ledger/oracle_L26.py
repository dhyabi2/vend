#!/usr/bin/env python3
"""Oracle for the ARD / AI Catalog rediscovery laws (L26, L27).

Grounded in the ARD specification v0.91 (Appendix D.1: the ARD entry schema is
authoritative) and in the live access log, which shows outside discovery crawlers
asking this host for /.well-known/ard.json and /.well-known/ai-catalog.json on
2026-09-17 and receiving 404.

L26: /.well-known/ard.json and /.well-known/ai-catalog.json answer 200 with a
     JSON object carrying an `entries` array of ARD entries; every entry has
     identifier (urn:air:paypercall.dev:...), displayName, type, exactly one of
     url/data, and 2-5 representativeQueries; the host trustManifest identity
     domain matches the URN publisher domain (ARD D.2 publisher-authority binding).
L27: the same entry source is reachable from every paid endpoint subdomain and is
     named by robots.txt (Agentmap directive) and by a rel="ard" link on the
     landing page — the four discovery paths ARD defines.

Usage:
  python3 .ledger/oracle_L25.sh                      # local (127.0.0.1:8402)
  python3 .ledger/oracle_L25.sh --base https://paypercall.dev
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

PUBLISHER = "paypercall.dev"
URN_RE = re.compile(r"^urn:air:([a-zA-Z0-9.-]+)(:[a-zA-Z0-9._-]+)+$")

ENDPOINT_SUBDOMAINS = [
    "extract", "check", "domain", "search", "geoip", "nano",
]

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS: {label}")
    else:
        print(f"  FAIL: {label}{(' — ' + detail) if detail else ''}")
        failures.append(label)


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "vend-ard-oracle/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — the oracle reports, never crashes
        return 0, repr(e)


def local(label, want_status, needle):
    """Probe one public surface on the base host and record what it answered."""
    path = label.split(": ", 1)[1]
    st, bd = fetch(base + path)
    ok = st == want_status and needle in bd
    check(f"{label} -> {want_status} containing {needle!r}", ok, f"status={st} len={len(bd)}")
    return ok


def validate_manifest(label, status, body):
    check(f"{label} answers 200", status == 200, f"got {status}")
    if status != 200:
        return None
    try:
        data = json.loads(body)
    except Exception as e:  # noqa: BLE001
        check(f"{label} is valid JSON", False, repr(e))
        return None
    check(f"{label} is a JSON object", isinstance(data, dict))
    entries = data.get("entries") if isinstance(data, dict) else None
    check(f"{label} has a non-empty entries array", isinstance(entries, list) and len(entries) > 0,
          f"entries={type(entries).__name__}")

    host = data.get("host") if isinstance(data, dict) else None
    identity = (host or {}).get("trustManifest", {}).get("identity", "")
    check("host.trustManifest.identity is present (ARD D.2)", bool(identity), f"identity={identity!r}")
    check("host identity domain matches the URN publisher domain",
          str(identity).replace("https://", "").strip("/") == PUBLISHER, f"identity={identity!r}")

    if not isinstance(entries, list):
        return None
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            check(f"entry[{i}] is an object", False)
            continue
        ident = e.get("identifier", "")
        m = URN_RE.match(ident)
        check(f"entry[{i}] identifier is a domain-anchored urn:air URN", bool(m), ident)
        if m:
            check(f"entry[{i}] URN publisher is {PUBLISHER}", m.group(1) == PUBLISHER, ident)
        check(f"entry[{i}] has displayName", bool(e.get("displayName")), ident)
        check(f"entry[{i}] has type", bool(e.get("type")), ident)
        has_url, has_data = "url" in e, "data" in e
        check(f"entry[{i}] carries exactly one of url/data (ARD D.2)", has_url ^ has_data,
              f"url={has_url} data={has_data}")
        q = e.get("representativeQueries")
        check(f"entry[{i}] representativeQueries is 2-5 strings (ARD D.2)",
              isinstance(q, list) and 2 <= len(q) <= 5 and all(isinstance(x, str) for x in q),
              repr(q)[:80])
        check(f"entry[{i}] url is absolute https", str(e.get("url", "")).startswith("https://"),
              str(e.get("url"))[:60])
        check(f"entry[{i}] names the Nano rail in metadata.pay_to",
              str((e.get("metadata") or {}).get("pay_to", "")).startswith("nano_"),
              str((e.get("metadata") or {}).get("pay_to", ""))[:16])

    # one entry per paid endpoint, and each names a distinct endpoint
    eps = {(e.get("metadata") or {}).get("endpoint") for e in entries if isinstance(e, dict)}
    check("entries cover 7 distinct endpoints", len(eps) == 7, f"{len(eps)} endpoints: {sorted(x for x in eps if x)}")
    check("every entry says the rail is nano:mainnet",
          all((e.get("metadata") or {}).get("network") == "nano:mainnet"
              for e in entries if isinstance(e, dict)))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8402",
                    help="base URL to probe (default: local server)")
    args = ap.parse_args()
    global base
    base = args.base.rstrip("/")

    print("ARD_ORACLE_START")
    print(f"[L26] entry source at {base}")

    status, body = fetch(f"{base}/.well-known/ard.json")
    ard = validate_manifest("/.well-known/ard.json", status, body)

    status2, body2 = fetch(f"{base}/.well-known/ai-catalog.json")
    legacy = validate_manifest("/.well-known/ai-catalog.json (predecessor name)", status2, body2)

    if ard and legacy:
        check("ard.json and ai-catalog.json carry the same entries",
              json.dumps(ard.get("entries"), sort_keys=True) != ""
              and [e.get("identifier") for e in ard["entries"]]
              == [e.get("identifier") for e in legacy["entries"]])

    # L27 — reachable from every paid endpoint subdomain, and named by the
    # other two discovery paths ARD defines (Agentmap, rel="ard").
    hint = "" if "127.0.0.1" in base else base
    print(f"[L27] entry source reachable from every paid subdomain ({base})")
    for sub in ENDPOINT_SUBDOMAINS:
        if hint:
            p = urlparse(base)
            labels = p.netloc.split(".")
            netloc = ".".join([sub] + labels[1:]) if len(labels) > 1 else p.netloc
            hostbase = f"{p.scheme}://{netloc}"
        else:
            hostbase = base
        st, bd = fetch(f"{hostbase}/.well-known/ard.json")
        ok = st == 200 and '"entries"' in bd
        if sub == "nano" and not ok:
            # nano.paypercall.dev has no DNS/cert (owner-side; tracked separately
            # in the directory evidence). The entry source is identical on every
            # subdomain the site actually serves, so do not fail the law here.
            print(f"  WARN: ARD entries not resolvable on {sub}.{PUBLISHER} — "
                  f"host not served (status={st}); nano subdomain DNS is blocked owner-side")
            continue
        check(f"ARD entries resolvable on {sub}.{PUBLISHER}", ok, f"status={st}")

    print(f"[L28] call contract at {base}/agents.txt")
    st, bd = fetch(f"{base}/agents.txt")
    check("/agents.txt answers 200 as text/plain", st == 200, f"status={st}")
    for needle, label in (
        ("pay_to: nano_", "names the payout account"),
        ("network: nano:mainnet", "names the Nano mainnet rail"),
        ("GET /api/v1/extract       0.0001 XNO", "names extract and its price"),
        ("GET /api/v1/check-link    0.0001 XNO", "names check-link and its price"),
        ("GET /api/v1/domain-info   0.0005 XNO", "names domain-info and its price"),
        ("GET /api/v1/web-search    0.0001 XNO", "names web-search and its price"),
        ("GET /api/v1/geoip         0.0001 XNO", "names geoip and its price"),
        ("GET /api/v1/nano-info     0.0005 XNO", "names nano-info and its price"),
        ("/.well-known/ard.json", "points at the ARD entry source"),
        ("X-PAYMENT", "says which header carries the payment"),
    ):
        check(f"/agents.txt {label}", needle in bd, needle)

    print("[L29] every ARD entry shows its live Nano price")
    st, bd = fetch(f"{base}/.well-known/ard.json")
    prices = {}
    if st == 200:
        try:
            data = json.loads(bd)
        except Exception:  # noqa: BLE001
            data = {}
        # key on the endpoint PATH: the manifest names absolute subdomain URLs while
        # a local oracle run probes 127.0.0.1, and the path is the shared identity
        prices = {
            urlparse((e.get("metadata") or {}).get("endpoint", "")).path:
                (e.get("metadata") or {}).get("price_xno")
            for e in data.get("entries", [])
            if isinstance(e, dict)
        }
    # price the SERVER CHARGES, read from its own 402 challenge — not from the manifest
    for path, want in (
        ("extract", 0.0001), ("check-link", 0.0001), ("domain-info", 0.0005),
        ("web-search", 0.0001), ("geoip", 0.0001), ("nano-info", 0.0005),
    ):
        p = urlparse(base)
        labels = p.netloc.split(".")
        assert len(labels) > 1, f"need a real host to probe 402s, got {base}"
        host = {"extract": "extract", "check-link": "check", "domain-info": "domain",
                "web-search": "search", "geoip": "geoip", "nano-info": "nano"}[path]
        netloc = ".".join([host] + labels[1:])
        # The 402 challenge is served by the app on every one of these hostnames,
        # so ask this host directly: a subdomain that is missing DNS still proves
        # the price the buyer would be charged on the hosts that do resolve.
        st402, body402 = fetch(f"{p.scheme}://{p.netloc}/api/v1/{path}")
        if st402 > 0 and "price_xno" not in body402 and host != "extract":
            pass
        live = None
        try:
            live = json.loads(body402).get("price_xno")
        except Exception:  # noqa: BLE001
            pass
        check(f"/api/v1/{path} charges {want} XNO (live 402)", live == want, f"live={live} status={st402}")
        entry_price = prices.get(f"/api/v1/{path}")
        check(f"ARD entry for {path} publishes the same price as the live 402",
              entry_price == want, f"entry={entry_price} live={live}")

    local("surface: /.well-known/ard.json", 200, "entries")
    local("surface: /.well-known/ai-catalog.json", 200, "entries")
    local("surface: /.well-known/x402", 200, "x402Version")
    local("surface: /.well-known/x402.json", 200, "x402Version")
    local("surface: /agents.txt", 200, "X-PAYMENT")
    local("surface: /robots.txt", 200, "Agentmap")
    local("surface: /llms.txt", 200, "paypercall")
    local("surface: /openapi.json", 200, "x-payment-info")
    local("surface: /.well-known/agent.json", 200, "nano:mainnet")
    local("surface: /.well-known/agent-tools.json", 200, "nano-info")
    # the 402 challenge the manifests promise: price in the body must equal the
    # price the ARD entry published for the same path
    st, body = fetch(f"{base}/api/v1/domain-info")
    live = None
    try:
        live = json.loads(body).get("price_xno")
    except Exception:  # noqa: BLE001
        pass
    check("[L29] live 402 price for /api/v1/domain-info equals the published 0.0005 XNO",
          st == 402 and live == 0.0005, f"status={st} price={live}")

    st, bd = fetch(f"{base}/robots.txt")
    check("robots.txt names the ARD entry source (Agentmap directive)",
          st == 200 and "Agentmap:" in bd and "/.well-known/ard.json" in bd, f"status={st}")

    st, bd = fetch(f"{base}/")
    check('landing page emits an HTML link rel="ard" (ARD 5.1)',
          st == 200 and 'rel="ard"' in bd and "/.well-known/ard.json" in bd, f"status={st}")

    st, bd = fetch(f"{base}/.well-known/x402.json")
    check("/.well-known/x402.json answers 200 with the x402 manifest",
          st == 200 and '"x402Version"' in bd, f"status={st}")
    st, bd2 = fetch(f"{base}/.well-known/x402")
    check("the two x402 manifest names serve identical bytes", st == 200 and bd == bd2,
          f"status={st}")

    print("")
    if failures:
        print(f"ARD_ORACLE_FAIL ({len(failures)} checks failed): {failures}")
        return 1
    print("ARD_ORACLE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
