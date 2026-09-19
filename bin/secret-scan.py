#!/usr/bin/env python3
"""Vend pre-publish secret scan — the gate between this box and anything public.

Usage:
    python3 bin/secret-scan.py --repo /root/vend [--tree] [--json]

Modes:
    default  scan every path in a wheel/sdist tarball or a snapshot directory
    --tree   scan the git TRACKED file list of the repository instead

Exit codes: 0 = clean, 2 = findings (nothing may be published), 3 = nothing to scan.

Rules live in secret_patterns.py so `.gitignore` and this gate cannot drift.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from fnmatch import fnmatch as _fnmatch
import tarfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from secret_patterns import content_is_secret, name_is_secret  # noqa: E402

ARCHIVES = (".whl", ".tar.gz", ".zip", ".tgz")
MAX_READ = 2_000_000


def tracked_files(repo: str) -> list[str]:
    """Files git tracks (not the working tree: untracked junk is not published)."""
    try:
        out = subprocess.run(["git", "-C", repo, "ls-files", "-z"],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return []
        return [p for p in out.stdout.split("\0") if p]
    except (OSError, subprocess.SubprocessError):
        return []


def snapshot_files(root: str) -> list[str]:
    """Every file under a directory, as paths relative to that directory."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "node_modules")]
        for f in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, f), root))
    return found


def archive_members(path: str) -> list[str]:
    if path.endswith(".whl") or path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            return z.namelist()
    if path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path) as t:
            return [m.name for m in t.getmembers() if m.isfile()]
    return []


def read_from(path: str, member: str, limit: int = 4096) -> str:
    try:
        if path.endswith((".whl", ".zip")):
            with zipfile.ZipFile(path) as z:
                return z.read(member)[:limit].decode("utf-8", "replace")
        if path.endswith((".tar.gz", ".tgz")):
            with tarfile.open(path) as t:
                fh = t.extractfile(member)
                return fh.read(limit).decode("utf-8", "replace") if fh else ""
    except (KeyError, OSError, zipfile.BadZipFile, tarfile.TarError):
        return ""
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--tree", action="store_true",
                    help="scan git-tracked files instead of a built artifact")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-name", action="append", default=[],
                    metavar="GLOB",
                    help="exempt a path whose NAME rule matches but whose contents were reviewed "
                         "and found clean (recorded in the output; use for config files that "
                         "carry no secret). Never exempts a content finding.")
    args = ap.parse_args()

    findings: list[dict] = []
    exempted: list[dict] = []
    scanned = 0

    def name_verdict(rel: str) -> bool:
        """True when the path is exempted by an explicit, reviewed allowance."""
        for glob in args.allow_name:
            if _fnmatch(rel, glob) or _fnmatch(rel.lstrip("./"), glob):
                return True
        return False

    if args.tree:
        repo = Path(args.repo)
        for rel in tracked_files(args.repo):
            scanned += 1
            rule = name_is_secret(rel)
            if rule and name_verdict(rel):
                exempted.append({"file": rel, "why": f"reviewed name exemption ({rule})"})
            elif rule:
                findings.append({"file": rel, "why": f"secret-looking name ({rule})"})
                continue
            p = repo / rel
            try:
                if p.is_file() and p.stat().st_size <= MAX_READ:
                    text = p.read_text("utf-8", "replace")
                else:
                    text = ""
            except OSError:
                text = ""
            hit = content_is_secret(text)
            if hit:
                findings.append({"file": rel, "why": f"content: {hit}"})
    else:
        target = args.repo
        if os.path.isdir(target):
            for rel in snapshot_files(target):
                scanned += 1
                rule = name_is_secret(rel)
                if rule and name_verdict(rel):
                    exempted.append({"file": rel, "why": f"reviewed name exemption ({rule})"})
                elif rule:
                    findings.append({"file": rel, "why": f"secret-looking name ({rule})"})
        elif os.path.isfile(target):
            for member in archive_members(target):
                scanned += 1
                rule = name_is_secret(member)
                if rule and name_verdict(member):
                    exempted.append({"file": f"{os.path.basename(target)}:{member}",
                                     "why": f"reviewed name exemption ({rule})"})
                elif rule:
                    findings.append({"file": f"{os.path.basename(target)}:{member}",
                                     "why": f"secret-looking name ({rule})"})
                    continue
                hit = content_is_secret(read_from(target, member))
                if hit:
                    findings.append({"file": f"{os.path.basename(target)}:{member}",
                                     "why": f"content: {hit}"})
        else:
            print(f"nothing to scan at {target}", file=sys.stderr)
            return 3

    verdict = {"target": args.repo, "mode": "tree" if args.tree else "artifact",
               "scanned": scanned, "findings": findings, "exempted": exempted,
               "clean": not findings}
    print(json.dumps(verdict, indent=2) if args.json else
          (f"clean: {scanned} file(s) scanned, no live secret"
           if not findings else
           "REFUSED: " + "; ".join(f"{f['file']} ({f['why']})" for f in findings)))
    return 0 if not findings else 2


if __name__ == "__main__":
    sys.exit(main())
