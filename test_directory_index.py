#!/usr/bin/env python3
"""Unit tests for bin/directory_index.py (corrective-action hardening block)."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))
import directory_index as di  # noqa: E402


def test_load_good_file_round_trip():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "good.json")
    with open(p, "w") as fh:
        json.dump({"listings": [{"directory": "D", "url": "https://x", "status": "verified"}]}, fh)
    data, st = di.load_index(p)
    assert st["source"] == "disk" and not st["recovered"]
    assert data["listings"][0]["name"] == ""  # safe default applied


def test_corrupt_file_recovered_to_skeleton():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "bad.json")
    with open(p, "w") as fh:
        fh.write("{ not json")
    data, st = di.load_index(p, use_git=False)
    assert st["recovered"] is True
    assert isinstance(data.get("listings"), list)


def test_missing_file_recovered():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "missing.json")
    data, st = di.load_index(p, use_git=False)
    assert st["recovered"] is True
    assert data["listings"] == []


def test_cached_copy_fallback():
    tmp = tempfile.mkdtemp()
    bad = os.path.join(tmp, "bad.json")
    cached = os.path.join(tmp, "cached.json")
    with open(bad, "w") as fh:
        fh.write("{ corrupt")
    with open(cached, "w") as fh:
        json.dump({"listings": [{"directory": "C", "url": "https://c", "status": "ok"}]}, fh)
    data, st = di.load_index(bad, cached_copy=cached, use_git=False)
    assert st["source"] == "cached" and st["recovered"] is True
    assert data["listings"][0]["directory"] == "C"


def test_quarantine_malformed_and_enrich_defaults():
    mixed = {"listings": [
        {"directory": "A", "url": "https://a", "status": "ok"},
        {"url": "https://no-dir"},
        "not-a-dict",
        {"directory": "B", "url": "https://b", "status": "ok", "name": "B"},
    ]}
    data, q = di._enrich_and_quarantine(mixed)
    assert q == 2
    assert len(data["listings"]) == 2
    names = {l["name"] for l in data["listings"]}
    assert "" in names and "B" in names
    # every enriched listing carries every default key -> no KeyError ever
    for l in data["listings"]:
        for k in di.LISTING_DEFAULTS:
            assert k in l


def test_report_never_raises_and_is_partial():
    data = {"listings": [
        {"directory": "A", "url": "u", "status": "ok", "name": "a"},
        {"directory": "B", "url": "u", "status": "verified", "name": "b"},
    ], "probe": {"all_healthy": True, "endpoints_ok": 2, "endpoints_total": 2}}
    rep = di.render_report(data)
    assert isinstance(rep, str) and rep.startswith("# Vend Directory Report")
    assert "Listings: 2" in rep
    assert "verified=1" in rep and "ok=1" in rep
    # garbage input still yields a string (never raises)
    assert isinstance(di.render_report(None), str)
    assert isinstance(di.render_report(42), str)


def test_git_reconstruction_returns_valid_or_none():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "x.json")
    with open(p, "w") as fh:
        fh.write(json.dumps({"listings": []}))
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "x.json"], cwd=tmp, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], cwd=tmp, check=True)
    got = di._reconstruct_from_git(p)
    assert got is not None and isinstance(got.get("listings"), list)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    if failed:
        sys.exit(1)
    print("ALL_DIRECTORY_INDEX_TESTS_PASS")
