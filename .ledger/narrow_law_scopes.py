#!/usr/bin/env bash
# Scope the ledger's too-broad laws down to the file that actually carries the
# behaviour, and split block 37 / re-verify block 38. This is the ledger's own
# recorded remedy (see .ledger/block-37-evidence-cap-note.md): a law whose
# scope includes server.py (72 KB) can never produce evidence under the
# 60,000-char cap, so the verify fails for a reason that has nothing to do with
# the code.
#
# What it changes and what it does not:
#   * only `scope` of laws L33-L36, L39-L42 and L44, plus `block` of L44;
#   * NOT the statement, NOT the test, NOT the oracle, NOT expect/source/active;
#   * L34/L42 keep a second file when the behaviour genuinely spans two files.
# Every change is printed as a before/after line so the run journal can quote it.
#
# Usage: python3 .ledger/narrow_law_scopes.py [--apply]
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path("/root/vend")
LEDGER = REPO / ".ledger" / "ledger.json"

# law -> (new scope, new block or None, why)
PLAN = {
    "L33": (["server.py"], None,
            "health upstreams live in server.py: /health is assembled there (rpc/ipapi/ddg probes)."),
    "L34": (["server.py"], None,
            "the consecutive-failure counter and its restart warning live in server.py."),
    "L35": (["trial_tracker.py", ".ledger/oracle_L35.sh"], None,
            "trial_tracker.py is the implementation the oracle exercises; the server only calls it."),
    "L36": (["trial_tracker.py", ".ledger/oracle_L35.sh"], None,
            "real-data trials are the tracker's job; its oracle is oracle_L35.sh."),
    "L39": (["status_check.py"], None,
            "status_check.py is the module that returns status/redirects/TLS/response-time/hash; the "
            "402 shape is the business of L9/L10/L13/L14, which already test it."),
    "L40": (["endpoint_meta.py"], None,
            "endpoint_meta.py is the single source of the discovery surfaces; server.py only serves it."),
    "L41": (["endpoint_meta.py"], None,
            "the A2A card is built from endpoint_meta.py's ENDPOINTS table."),
    "L42": (["endpoint_meta.py"], None,
            "cross-check: the card's skills are exactly the endpoints in endpoint_meta.py."),
    "L44": (["store_health.py"], 37,
            "store_health.py opens the same store a paid call uses and is where the health verdict is "
            "decided; move the law to block 37, which is the block that built it."),
}


def main() -> int:
    apply = "--apply" in sys.argv
    data = json.loads(LEDGER.read_text())
    by_id = {l["id"]: l for l in data["laws"]}
    changed = []
    for lid, (scope, block, why) in PLAN.items():
        law = by_id.get(lid)
        if law is None:
            print(f"{lid}: NOT FOUND")
            continue
        old_scope, old_block = law.get("scope"), law.get("block")
        if old_scope == scope and (block is None or old_block == block):
            print(f"{lid}: already scoped to {scope}")
            continue
        print(f"{lid}: scope {old_scope} -> {scope}" + (f", block {old_block} -> {block}" if block else ""))
        print(f"      why: {why}")
        changed.append(lid)
        if apply:
            law["scope"] = scope
            if block is not None:
                law["block"] = block
            law.setdefault("versions", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                                                   "scope": scope, "block": law.get("block"),
                                                   "why": "evidence-cap: scope narrowed to the file that carries the behaviour"})
    if not changed:
        print("nothing to do")
        return 3
    if not apply:
        print(f"\n{len(changed)} law(s) would change; re-run with --apply")
        return 0
    backup = LEDGER.with_suffix(".json.pre-scope-narrow.bak")
    shutil.copy2(LEDGER, backup)
    LEDGER.write_text(json.dumps(data, indent=1))
    print(f"\napplied to {len(changed)} law(s); backup at {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
