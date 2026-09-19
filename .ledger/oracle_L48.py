#!/usr/bin/env python3
"""Oracle L48 — a dot-prefixed secret name at the repo root is refused.

Law: "The shared rule set refuses dot-prefixed secret names wherever they sit,
including the repository root."  Scope: secret_patterns.py.

Negative control: a plain source filename, and a name that merely CONTAINS a
secret word without being one, must be allowed — a matcher that refuses
everything proves nothing.  No key-shaped fixture is written anywhere (see
.ledger/oracle_L46.py): plain names only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from secret_patterns import name_is_secret  # noqa: E402

MUST_REFUSE = [
    ".env",
    ".env.local",
    ".env.production",
    ".netrc",
    ".git-credentials",
    "credentials",
    "credentials.json",
    ".vivioo-edit-key.txt",
    "mcp-registry-key.pem",
    "mcp-registry-key.hex",
    "id_rsa",
    "id_ed25519",
    "deploy/vend.env",
    "keys/id_rsa",
    "var/something.pem",
    "vendor.key",
    "cert.p12",
    "bundled.pfx",
    "./.env",
]

MUST_ALLOW = [
    "server.py",
    "store.py",
    "secret_patterns.py",
    "bin/secret-scan.py",
    "journal/2026-09-17-keyless-directories.md",
    "docs/environment.md",
    "envoy.py",
    "keyboard.py",
    "keyless.md",
    "credential_helper_notes.md",
    ".gitignore",
    ".githooks/pre-commit",
]

fail = 0
for name in MUST_REFUSE:
    rule = name_is_secret(name)
    if rule is None:
        print(f"L48_FAIL: {name!r} was allowed")
        fail = 1
for name in MUST_ALLOW:
    rule = name_is_secret(name)
    if rule is not None:
        print(f"L48_FAIL: {name!r} was refused by {rule} (false positive)")
        fail = 1

print("L48_" + ("PASS" if not fail else "FAIL"),
      f"({len(MUST_REFUSE)} refused, {len(MUST_ALLOW)} allowed)")
sys.exit(fail)
