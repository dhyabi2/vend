#!/usr/bin/env python3
"""Shared secret-scan rules for Vend.

One place for the two rules that must agree:
  * `.gitignore` — what git is allowed to track;
  * `bin/secret-scan.py` — the pre-publish gate.

Keep this list short and specific: a rule that matches source code makes the
gate useless and trains everyone to bypass it.
"""
import re

# Filenames/globs that must never be tracked or published.
NAME_PATTERNS = [
    r"\.env$",
    r"\.env\.",
    r"\.env\.(?:local|prod|production|staging|stage|dev|old|bak|backup|save|live)$",
    r"(^|/)mcp-registry-key\.(pem|hex)$",
    r"\.pem$",
    r"\.key$",
    r"\.pfx$",
    r"(^|/)id_rsa$",
    r"(^|/)id_ed25519$",
    r"\.p12$",
    r"\.vivioo-edit-key",
    r"(^|/)credentials(\.json)?$",
    r"(^|/)\.netrc$",
    r"(^|/)\.git-credentials$",
]

# Content patterns that indicate a live secret, not a mention of one.
CONTENT_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "private key block"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "openai-style API key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "github token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "slack token"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.", "JWT"),
]

PRIVATE_KEY_MARKERS = (
    "private_key", "private-key", "privatekey", "seed_hex", "secret_key",
    "secret-key", "BEGIN PRIVATE KEY",
)


def nano_seed(text: str) -> bool:
    """A bare 64-hex string that is labelled as a key — not a public address."""
    import re as _re
    for m in _re.finditer(r"(?<![A-Za-z0-9])([0-9A-Fa-f]{64})(?![A-Za-z0-9])", text):
        window = text[max(0, m.start() - 80): m.end() + 80].lower()
        if any(marker in window for marker in PRIVATE_KEY_MARKERS):
            return True
    return False

NAME_RE = [re.compile(p) for p in NAME_PATTERNS]


def name_is_secret(path: str) -> str | None:
    """Return the matching rule when a path looks like a secret file.

    Only a literal leading "./" is stripped.  Stripping DOTS as well (the old
    `lstrip("./")`) erased the leading dot of root-level dot-files, so `.env`,
    `.netrc`, `.git-credentials` and `.vivioo-edit-key.txt` — exactly the names
    that hold credentials — never matched a rule.
    """
    p = path.strip()
    while p.startswith("./"):
        p = p[2:]
    for rx in NAME_RE:
        if rx.search(p):
            return rx.pattern
    return None


def content_is_secret(text: str) -> str | None:
    """Return the description of the first live-secret pattern found."""
    for rx, label in CONTENT_PATTERNS:
        if re.search(rx, text):
            return label
    if nano_seed(text):
        return "nano private key or seed (64-hex next to a key label)"
    return None
