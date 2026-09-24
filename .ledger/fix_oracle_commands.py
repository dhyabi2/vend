#!/usr/bin/env python3
"""Repair oracle command lines that cannot run, and report what was repaired.

Why: the ledger executes each law's recorded oracle as-is. Two laws were
recorded without an interpreter path (`.ledger/oracle_L43.sh`,
`.ledger/oracle_L47.sh`), so the executor ran them through /bin/sh and reported
`exit 126: Permission denied` — the law then failed the judge for "missing
evidence" while the oracle itself passes by hand. `bin/oracle-tracker.sh` found
them.

This is a repair of a recorded command, and it is treated as one: only the
interpreter prefix is added, the test, statement, scope and oracle file are
untouched, and the change is recorded in the law's `versions` with a reason.

Usage:
    python3 .ledger/fix_oracle_commands.py            # report only
    python3 .ledger/fix_oracle_commands.py --apply
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "ledger.json"


def interpreter_for(path: str) -> str:
    if path.endswith(".py"):
        return "python3"
    if path.endswith((".sh", ".bash")):
        return "bash"
    return ""


def main() -> int:
    apply = "--apply" in sys.argv
    data = json.loads(LEDGER.read_text())
    fixed = []
    for law in data["laws"]:
        cmd = (law.get("oracle") or "").strip()
        if not cmd:
            continue
        first = cmd.split()[0]
        if first in ("bash", "sh", "python3", "python"):
            continue
        interp = interpreter_for(first)
        if not interp or not (LEDGER.parent.parent / first).exists():
            continue
        new = f"{interp} {cmd}"
        print(f"{law['id']}: {cmd!r} -> {new!r}")
        fixed.append(law["id"])
        if apply:
            law["oracle"] = new
            law.setdefault("versions", []).append({
                "at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                "oracle": new,
                "why": "the recorded command had no interpreter; the executor ran it via /bin/sh and it exited 126",
            })
    if not fixed:
        print("no oracle command needs repair")
        return 0
    if not apply:
        print(f"\n{len(fixed)} command(s) would change; re-run with --apply")
        return 0
    backup = LEDGER.with_suffix(".json.pre-oracle-fix.bak")
    shutil.copy2(LEDGER, backup)
    LEDGER.write_text(json.dumps(data, indent=1))
    print(f"\nrepaired {len(fixed)} command(s); backup at {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
