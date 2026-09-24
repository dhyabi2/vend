#!/usr/bin/env python3
"""Measure each law's evidence size exactly the way the ledger's verifier does.

Why this exists: `TooBroad` is raised deep inside a verify run, after every
oracle in the block has already been executed (the block-38 verify burned over
an hour across two runs on laws that could never fit the 60,000-char cap). This
reproduces `ledger_evidence.law_evidence` with no oracle run and no judge call,
so the too-broad laws are known before a single model request is spent, and the
files that actually fit can be chosen from numbers instead of guesses.

It uses the ledger's own module, so the number it prints is the number the
verifier computes; it does not re-implement the rule.

Usage:
    python3 .ledger/evidence_budget.py                 # every active law
    python3 .ledger/evidence_budget.py --block 38      # only laws a block-38 verify sends
    python3 .ledger/evidence_budget.py --files server.py store.py   # what fits on this scope?
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, "/root/invent-stack/bin")

from ledger_evidence import CAP, TooBroad, law_evidence  # noqa: E402

REPO = HERE.parent
LEDGER = HERE / "ledger.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", type=float, default=None)
    ap.add_argument("--files", nargs="*", default=None,
                    help="instead of a law: report the evidence budget for this scope")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    data = json.loads(LEDGER.read_text())

    if args.files is not None:
        law = {"id": "SCOPE", "scope": args.files, "block": 0}
        try:
            ev, _ = law_evidence(data, law)
            print(f"scope {args.files}: {len(ev)} chars (cap {CAP}) — fits")
            return 0
        except TooBroad as ex:
            print(f"scope {args.files}: TOO BROAD — {ex}")
            return 2

    rows = []
    for law in data["laws"]:
        if law.get("retired"):
            continue
        if args.block is not None and law.get("block", 0) > args.block:
            continue
        try:
            ev, _ = law_evidence(data, law)
            rows.append({"id": law["id"], "block": law.get("block"), "scope": law.get("scope"),
                         "chars": len(ev), "fits": True})
        except TooBroad as ex:
            want = int(str(ex).split("needs ")[1].split(" chars")[0])
            rows.append({"id": law["id"], "block": law.get("block"), "scope": law.get("scope"),
                         "chars": want, "fits": False})

    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    bad = [r for r in rows if not r["fits"]]
    for r in rows:
        flag = "ok  " if r["fits"] else "OVER"
        print(f"{flag} {r['id']:<4} block {str(r['block']):<5} {r['chars']:>8} chars  {r['scope']}")
    print(f"\n{len(bad)} of {len(rows)} law(s) exceed the {CAP}-char cap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
