#!/usr/bin/env python3
"""Hardened load / enrich / validate / report for static/vend-directories.json.

Implements corrective-action block (2026-09-25 21:20 UTC):
  1. Validate and repair the index: check existence, parse defensively, fall
     back to a cached copy or to git-history reconstruction if unavailable.
  2. Enrich every listing entry with safe defaults so consumers never hit
     KeyError on a missing key.
  3. Persistent, testable module (refactor of the inline heredoc report path).
  4. Schema validator that quarantines malformed entries instead of crashing
     the whole run.
  5. Report generation wrapped in try/except: a partial report is always
     returned and the failure is logged for the next attempt.
  6. Self-healing step that reconstructs missing directory listings from git
     history if the file is corrupt.

Never raises on load: every entry point returns a usable structure plus a
human-readable status, so the serving/update/report pipeline stays up even
when the on-disk file is missing or malformed.
"""

import json
import os
import subprocess
import sys
import time

# --- Corrective #2: safe defaults for every listing key that any consumer reads
LISTING_DEFAULTS = {
    "directory": "",
    "url": "",
    "status": "unknown",
    "note": "",
    "name": "",
    "server_name": "",
    "mcp_url": "",
    "auth_method": "",
    "api_id": "",
    "listing_id": "",
    "submission_id": "",
    "submitted_at": "",
    "published_at": "",
    "verified_at": "",
    "verified": False,
    "version": "",
}

# Minimum keys a listing must carry to be considered well-formed (#4).
REQUIRED_LISTING_KEYS = ("directory", "url", "status")


def load_index(path, cached_copy=None, use_git=True, timeout=15):
    """Load and validate the directory index, never raising.

    Order of recovery (corrective #1, #6):
      1. Read + parse the on-disk file (bounded by ``timeout`` via subprocess
         for a truly pathological file is overkill; we bound JSON parsing by
         size instead).
      2. If missing/corrupt and ``cached_copy`` is a valid path, use it.
      3. If missing/corrupt and ``use_git`` is true, reconstruct the last good
         committed version from git history.
      4. If nothing is available, return a minimal sane skeleton.

    Returns (data, status) where ``status`` is a dict describing what happened
    and whether recovery was required.
    """
    status = {"source": "disk", "recovered": False, "quarantined": 0, "error": None}
    data = None
    raw_error = None

    # (1) Try on-disk file first.
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            if len(raw) > 50 * 1024 * 1024:  # bounded parse (corrective #1)
                raise ValueError("index exceeds 50MB safety bound")
            data = json.loads(raw)
        else:
            raw_error = f"file missing: {path}"
    except (OSError, ValueError, json.JSONDecodeError) as e:
        raw_error = f"{type(e).__name__}: {e}"
        status["error"] = raw_error

    if data is not None:
        data, status["quarantined"] = _enrich_and_quarantine(data)
        return data, status

    # (2) Fall back to a cached copy if one is available on disk.
    if cached_copy and os.path.isfile(cached_copy):
        try:
            with open(cached_copy, "r", encoding="utf-8") as fh:
                data = json.loads(fh.read())
            status.update({"source": "cached", "recovered": True})
        except (OSError, ValueError, json.JSONDecodeError) as e:
            status["error"] = f"cached fallback failed: {type(e).__name__}: {e}"

    # (3) Self-heal from git history (corrective #6).
    if data is None and use_git:
        git_data = _reconstruct_from_git(path)
        if git_data is not None:
            data = git_data
            status.update({"source": "git", "recovered": True})

    # (4) Last resort: minimal healthy skeleton — never crash the pipeline.
    if data is None:
        data = {
            "name": "vend-directories",
            "base_url": "",
            "listings": [],
            "probe": {"all_healthy": False, "endpoints_ok": 0, "endpoints_total": 0},
        }
        status.update({"source": "skeleton", "recovered": True})

    data, status["quarantined"] = _enrich_and_quarantine(data)
    return data, status


def _enrich_and_quarantine(data):
    """Apply safe defaults (#2) and drop malformed listings (#4).

    Returns (cleaned_data, number_quarantined). Does not mutate the input
    structure in place for the listings list; builds a fresh enriched list.
    """
    cleaned = []
    quarantined = 0
    listings = data.get("listings") if isinstance(data, dict) else None
    if not isinstance(listings, list):
        listings = []

    for entry in listings:
        if not isinstance(entry, dict):
            quarantined += 1
            continue
        # Malformed: missing any required key -> quarantine, never crash (#4).
        if not all(k in entry for k in REQUIRED_LISTING_KEYS):
            quarantined += 1
            continue
        # Enrich with safe defaults for every known consumer key (#2).
        enriched = dict(LISTING_DEFAULTS)
        enriched.update({k: v for k, v in entry.items() if k in LISTING_DEFAULTS})
        cleaned.append(enriched)

    # Always return the enriched, quarantined structure (dict case included),
    # so consumers never read a stale, un-enriched copy.
    if isinstance(data, dict):
        data = dict(data)
        data["listings"] = cleaned
        return data, quarantined
    return {"listings": cleaned, "probe": {}}, quarantined


def render_report(data, timestamp=None):
    """Render a partial distribution report, never raising (#5).

    Always returns a string. On any failure inside, it logs the failure to
    stderr and returns a partial report rather than aborting the caller.
    """
    try:
        if isinstance(data, dict):
            listings = data.get("listings") or []
            probe = data.get("probe") or {}
        else:
            listings = []
            probe = {}
        total = len(listings)
        by_status = {}
        for item in listings:
            st = item.get("status", "unknown") if isinstance(item, dict) else "unknown"
            by_status[st] = by_status.get(st, 0) + 1
        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lines = [
            f"# Vend Directory Report ({ts})",
            f"Listings: {total}",
            "By status: " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
            or "none",
            f"All healthy: {probe.get('all_healthy', False)} "
            f"({probe.get('endpoints_ok', 0)}/{probe.get('endpoints_total', 0)})",
        ]
        return "\n".join(lines) + "\n"
    except Exception as e:  # noqa: BLE001 - partial report per corrective #5
        sys.stderr.write(f"report generation failed: {type(e).__name__}: {e}\n")
        return f"# Vend Directory Report (partial — error {type(e).__name__})\nListings: unknown\n"


def _reconstruct_from_git(path):
    """Reconstruct the last good committed copy of ``path`` from git history."""
    path = os.path.abspath(path)
    fdir = os.path.dirname(path)
    try:
        # Discover the real git working-tree root (robust for any path depth),
        # then the relative path of the target within it.
        top = subprocess.run(
            ["git", "-C", fdir, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=15,
        )
        if top.returncode != 0 or not top.stdout.strip():
            return None
        repo = top.stdout.strip()
        rel = os.path.relpath(path, repo)
        # Last commit that touched this file, then read its blob.
        cur = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=15,
        )
        commit = cur.stdout.strip()
        if not commit:
            return None
        show = subprocess.run(
            ["git", "-C", repo, "show", f"{commit}:{rel}"],
            capture_output=True, text=True, timeout=15,
        )
        if show.returncode != 0:
            return None
        return json.loads(show.stdout)
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError) as e:
        sys.stderr.write(f"git reconstruction failed: {type(e).__name__}: {e}\n")
        return None


def healthy(data):
    """Quick boolean used by callers that gate on a live, parseable index."""
    return isinstance(data, dict) and isinstance(data.get("listings"), list)


def _selftest():
    import tempfile
    tmp = tempfile.mkdtemp()
    good = os.path.join(tmp, "good.json")
    broken = os.path.join(tmp, "broken.json")
    missing = os.path.join(tmp, "missing.json")

    # good file round-trips
    with open(good, "w") as fh:
        json.dump({"listings": [{"directory": "D", "url": "https://x", "status": "verified"}]}, fh)
    data, st = load_index(good)
    assert st["source"] == "disk" and not st["recovered"], st
    assert data["listings"][0]["name"] == ""  # enriched with default
    assert data["listings"][0]["status"] == "verified"

    # corrupt file -> recovered (git or skeleton), never crash
    with open(broken, "w") as fh:
        fh.write("{ not json !!!")
    data2, st2 = load_index(broken, use_git=False)
    assert st2["recovered"] is True, st2
    assert isinstance(data2.get("listings"), list), data2

    # missing file -> recovered skeleton, never crash
    data3, st3 = load_index(missing, use_git=False)
    assert st3["recovered"] is True and data3["listings"] == []

    # malformed entry quarantined, well-formed kept
    mixed = {"listings": [
        {"directory": "A", "url": "https://a", "status": "ok"},
        {"url": "https://no-dir"},          # missing directory -> quarantine
        "not-a-dict",                        # non-dict -> quarantine
        {"directory": "B", "url": "https://b", "status": "ok", "name": "B-name"},
    ]}
    data4, q = _enrich_and_quarantine(mixed)
    assert q == 2, q
    assert len(data4["listings"]) == 2
    names = {l["name"] for l in data4["listings"]}
    assert "" in names and "B-name" in names  # defaults applied

    # report never raises and is a non-empty string
    rep = render_report(data4)
    assert isinstance(rep, str) and rep.startswith("# Vend Directory Report")
    assert "Listings: 2" in rep

    print("DIRECTORY_INDEX_SELFTEST_PASS")


if __name__ == "__main__":
    _selftest()
