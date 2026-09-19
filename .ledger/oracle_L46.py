#!/usr/bin/env python3
"""L46 oracle: the ledger's own test scripts never carry a key-shaped literal.

The ledger is tracked in git, so an oracle that spells out a dummy private key or
a token to test the secret gate publishes the very shape the gate exists to
catch — and it made pushes impossible on 2026-09-19 (the gate refused the repo
because of an oracle that was *testing* the gate). Every such fixture must be
assembled at run time instead.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/root/vend")
LEDGER = REPO / ".ledger"

SHAPES = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a literal PEM private key header"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "a github token literal"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "an API key literal"),
]


def main() -> int:
    files = sorted(subprocess.run(["git", "-C", str(REPO), "ls-files", ".ledger"],
                                  capture_output=True, text=True).stdout.split())
    if not files:
        print("FAIL: no tracked ledger files found to check")
        return 1
    bad = []
    for rel in files:
        p = REPO / rel
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text("utf-8", "replace")
        except OSError:
            continue
        for rx, label in SHAPES:
            if rx.search(text):
                bad.append(f"{rel}: {label}")
    if bad:
        print("FAIL: the ledger carries a key-shaped literal: " + "; ".join(bad))
        return 1
    print(f"PASS: {len(files)} tracked ledger files, no key-shaped fixture literal")
    print("L46_LEDGER_FIXTURE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
