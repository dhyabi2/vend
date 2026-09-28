#!/usr/bin/env python3
"""Deploy-parity checker: is every paid x402 endpoint a buyer can actually
discover on the OTHER live discovery surfaces (OpenAPI, llms.txt, agent tools)?

A buyer reaches Vend through whichever door an agent framework happens to use:
OpenAPI (SDK generators, proxy-style clients), llms.txt (documentation agents),
or .well-known/agent-tools.json (Claude-style tool discovery), or the x402
manifest itself. If a paid endpoint appears in the x402 manifest but is missing
from one of the other doors, a buyer who walks that door sees a smaller product —
and an endpoint nobody can discover earns nothing.

The x402 manifest is the source of truth for what is paid and live. This check
probes all four LIVE deployed surfaces and reports, per door, which paid
endpoints the door is missing (and which it wrongly advertises). No deploys,
no source builds — this measures what is actually serving buyers right now.

Usage:
    python3 bin/deploy-parity.py            # human-readable report
    python3 bin/deploy-parity.py --json     # machine-readable
Exit code 0 = every paid endpoint is discoverable on every door; 1 = drift.
"""
import argparse
import json
import re
import sys
import urllib.request

BASE = "https://extract.paypercall.dev"
DOORS = {
    "openapi": f"{BASE}/openapi.json",
    "llms": f"{BASE}/llms.txt",
    "agent_tools": f"{BASE}/.well-known/agent-tools.json",
}
UA = {"User-Agent": "vend-deploy-parity/1.0"}
TIMEOUT = 25


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode()


def x402_paid_paths():
    doc = json.loads(fetch(f"{BASE}/.well-known/x402"))
    paths = set()
    for r in doc.get("resources", []):
        if not (r.get("accepts") or r.get("wants")):
            continue  # free/documented endpoints are not payable; not part of the paid menu
        m = re.search(r"(/api/v1/[A-Za-z0-9_/-]+)", r.get("url", ""))
        if m:
            paths.add(m.group(1))
    return paths


def _api_paths_from_urls(urls):
    out = set()
    for u in urls:
        m = re.search(r"(/api/v1/[A-Za-z0-9_/-]+)", u or "")
        if m:
            out.add(m.group(1))
    return out


def openapi_paths():
    doc = json.loads(fetch(DOORS["openapi"]))
    return set(p for p in doc.get("paths", {}).keys() if p.startswith("/api/v1"))


def llms_paths():
    text = fetch(DOORS["llms"])
    return set(re.findall(r"/api/v1/[A-Za-z0-9_/-]+", text))


def agent_tools_paths():
    doc = json.loads(fetch(DOORS["agent_tools"]))
    return _api_paths_from_urls(
        r.get("url") or r.get("path") for r in doc.get("x402", {}).get("resources", [])
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    paid = x402_paid_paths()
    collectors = {
        "openapi": openapi_paths,
        "llms": llms_paths,
        "agent_tools": agent_tools_paths,
    }
    report = {"x402_paid_count": len(paid), "doors": {}}
    problems = False
    llms_text = None
    for door, fn in collectors.items():
        try:
            present = fn()
        except Exception as e:  # noqa: BLE001
            report["doors"][door] = {"error": str(e)}
            problems = True
            continue
        missing = sorted(paid - present)
        # llms.txt is prose: an endpoint row may use a bare name (e.g. | extract |
        # | url |) rather than the literal /api/v1/extract token. When a name
        # appears as a word in the llms text, count it as covered so a missing
        # /api/v1 literal does not produce a false drift on the prose door.
        overlooked = []
        if missing and door == "llms" and llms_text is None:
            llms_text = fetch(DOORS["llms"])
        for p in missing:
            name = p.rsplit("/", 1)[-1]
            if door == "llms" and re.search(rf"\b{re.escape(name)}\b", llms_text or ""):
                continue
            overlooked.append(p)
        report["doors"][door] = {
            "count": len(present),
            "missing_paid": overlooked,
            "extra_non_paid": sorted(present - paid),
        }
        if overlooked:
            problems = True

    report["in_parity"] = not problems
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"x402 paid endpoints live: {len(paid)}")
        for door, info in report["doors"].items():
            print(f"\n[{door}] {info.get('count', 'ERR')} paths")
            if info.get("error"):
                print("  ERROR:", info["error"])
                continue
            mp = info.get("missing_paid", [])
            if mp:
                print(f"  MISSING {len(mp)} PAID endpoints:", ", ".join(mp))
            else:
                print("  all paid endpoints discoverable here")
    print(f"\nIN PARITY: {report['in_parity']}")
    sys.exit(0 if report["in_parity"] else 1)


if __name__ == "__main__":
    main()
