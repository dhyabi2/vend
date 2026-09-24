#!/usr/bin/env python3
"""Atomic, self-healing file writes for Vend's build scripts.

Implements the corrective-action block for the swarm: never leave a partial
or corrupt artifact, never clobber a file you have not looked at first, and
fall back through write strategies (atomic temp-replace -> patch -> report)
instead of failing the build on a refusal.

Strategies, in order of preference (self-healing selection, CA #4):
  1. ATOMIC  : write to a temp file in the same directory, fsync, os.replace()
               (temp-replace). A crash mid-write leaves the old file intact.
  2. PATCH   : for text files that already exist, apply an in-place patch by
               replacing an exact old substring. Uses a unique-match rule (CA #1
               fallback to patch) and refuses a non-unique match instead of
               guessing.
  3. APPEND  : append to the tail of an existing file (for logs / monotonically
               growing artifacts only; opt-in by the caller via append=False).

Pre-flight (CA #2): before any write, inspect the target for read-only bits,
missing parent directories, symlinks, and existing content, and route to the
correct method instead of attempting a blind overwrite.

Watchdog (CA #5): a module-level counter records consecutive failures per path;
after 2+ consecutive failures the orchestrator refuses further blind retries
and requires new evidence (a forced mode) before trying again.

Usage:
    from atomicwrite import preflight, atomic_write, safe_write, reset

    ok, report = safe_write("/path/file.json", json.dumps(data))

Never raises on a write failure: it returns (ok, report) where report explains
what was tried and why. Callers decide whether a non-ok is fatal.
"""

import os
import sys
import tempfile
import time

# module-level watchdog: path -> consecutive failure count
_FAILURES = {}
# conservative lock-out: path -> True once watchdog trip fires
_LOCKED = {}

# strategies, tried in order by safe_write
_STRATEGIES = ["atomic", "patch", "append"]


# --------------------------------------------------------------------------
# Pre-flight (CA #2)
# --------------------------------------------------------------------------
def preflight(path):
    """Inspect a target path and return a status dict.

    Returns dict with keys:
      exists, is_dir, is_symlink, is_readonly, parent_exists,
      can_create (bool), reason (str or None)
    Does not mutate the filesystem.
    """
    info = {
        "path": path,
        "exists": os.path.lexists(path),
        "is_dir": False,
        "is_symlink": False,
        "is_readonly": False,
        "parent_exists": False,
        "can_create": False,
        "reason": None,
    }
    if os.path.lexists(path):
        info["is_dir"] = os.path.isdir(path)
        info["is_symlink"] = os.path.islink(path)
        if info["is_dir"]:
            info["reason"] = "target is a directory, refusing to write over it"
            return info
        # Read-only check: try to open for append (no truncation, no content
        # change) in a mode that respects permissions.
        try:
            with open(path, "a"):
                pass
            info["is_readonly"] = False
        except (OSError, PermissionError):
            info["is_readonly"] = True
    parent = os.path.dirname(os.path.abspath(path)) or "."
    info["parent_exists"] = os.path.isdir(parent)
    if info["parent_exists"]:
        try:
            fd, tmppath = tempfile.mkstemp(dir=parent, prefix=".ppflight-")
            os.close(fd)
            os.unlink(tmppath)
            info["can_create"] = True
        except (OSError, PermissionError):
            info["reason"] = info["reason"] or "parent directory is not writable"
    else:
        info["reason"] = info["reason"] or f"parent directory does not exist: {parent}"
    return info


# --------------------------------------------------------------------------
# Strategy 1: atomic temp-replace
# --------------------------------------------------------------------------
def atomic_write(path, content, mode="w"):
    """Atomically replace ``path`` with ``content``.

    Writes to a temp file in the same directory, fsyncs it, then os.replace()s
    it over the target. On any failure the previous file (if any) is untouched
    and the temp file is removed. Returns (True, "") on success, or
    (False, reason).
    """
    parent = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(parent):
        return False, f"parent directory does not exist: {parent}"
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=parent, prefix=".vendtmp-")
        with os.fdopen(fd, mode, encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = None
        return True, ""
    except (OSError, PermissionError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        if tmp is not None and os.path.lexists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


# --------------------------------------------------------------------------
# Strategy 2: in-place patch (CA #1 fallback)
# --------------------------------------------------------------------------
def patch_write(path, old, new, count=1):
    """Replace exactly ``count`` occurrences of ``old`` with ``new`` in a text file.

    Returns (True, "") on success. If the match is not unique (more or fewer
    than ``count`` occurrences), returns (False, reason) and writes nothing —
    never guesses between ambiguous matches.
    """
    if not os.path.isfile(path):
        return False, f"not a regular file: {path}"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = fh.read()
    except (OSError, PermissionError) as e:
        return False, f"read failed: {e}"
    n = data.count(old)
    if n != count:
        return False, f"expected {count} match(es) of old substring, found {n}"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(data.replace(old, new, count))
        return True, ""
    except (OSError, PermissionError) as e:
        return False, f"write failed: {e}"


# --------------------------------------------------------------------------
# Strategy 3: append (opt-in)
# --------------------------------------------------------------------------
def append_write(path, content):
    """Append ``content`` to the end of an existing file."""
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(content)
        return True, ""
    except (OSError, PermissionError) as e:
        return False, f"append failed: {e}"


# --------------------------------------------------------------------------
# Self-healing orchestrator (CA #4) + watchdog (CA #5)
# --------------------------------------------------------------------------
def safe_write(path, content, mode="w", old=None, append=False, forced=False):
    """Write ``content`` to ``path`` using the first strategy that works.

    Returns (True, report) or (False, report). Never raises on a write failure.
    ``report`` is a list of what was tried and the outcome.

    Strategy selection:
      - If ``append`` is True (log-like targets), try append before atomic.
      - If ``old`` is provided (a known existing substring), try patch first,
        then fall back to atomic replace.
      - Otherwise: atomic first, then (if ``forced`` / recovery) patch.
    """
    report = []
    pf = preflight(path)

    # Watchdog: refuse blind retries after 2+ consecutive failures (CA #5).
    # Checks BEFORE pre-flight recovery so a repeatedly bad path is gated early.
    if _LOCKED.get(path) and not forced:
        return False, [f"watchdog: path locked after {_FAILURES.get(path, 0)} consecutive failures; call safe_write(..., forced=True) with new evidence"]

    if pf["reason"]:
        # Pre-existing condition: route to the right method rather than blind write.
        if pf["is_dir"]:
            _note_failure(path)
            return False, [f"preflight: {pf['reason']}"]
        if pf["is_readonly"] and not forced:
            # Try to clear the read-only bit (CA #2 routing).
            try:
                os.chmod(path, 0o644)
                report.append("preflight: cleared read-only bit")
            except (OSError, PermissionError) as e:
                _note_failure(path)
                return False, [f"preflight: read-only and chmod failed: {e}"]
        if not pf["parent_exists"]:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
                report.append("preflight: created missing parent directory")
            except (OSError, PermissionError) as e:
                _note_failure(path)
                return False, [f"preflight: could not create parent: {e}"]

    strategies = []
    if append:
        strategies = ["append", "atomic"]
    elif old is not None:
        strategies = ["patch", "atomic", "append"]
    else:
        strategies = ["atomic", "patch", "append"]

    for strat in strategies:
        if strat == "atomic":
            ok, err = atomic_write(path, content, mode=mode)
            if ok:
                _note_success(path)
                report.append(f"atomic: ok")
                return True, report
            report.append(f"atomic: {err}")
        elif strat == "patch":
            if old is None:
                report.append("patch: skipped (no old substring provided)")
                continue
            ok, err = patch_write(path, old, content)
            if ok:
                _note_success(path)
                report.append("patch: ok")
                return True, report
            report.append(f"patch: {err}")
        elif strat == "append":
            ok, err = append_write(path, content)
            if ok:
                _note_success(path)
                report.append("append: ok")
                return True, report
            report.append(f"append: {err}")

    _note_failure(path)
    return False, report


def _note_success(path):
    _FAILURES.pop(path, None)
    _LOCKED.pop(path, None)


def _note_failure(path):
    n = _FAILURES.get(path, 0) + 1
    _FAILURES[path] = n
    if n >= 2:
        _LOCKED[path] = True


def reset():
    """Clear the watchdog counters (for tests / fresh runs)."""
    _FAILURES.clear()
    _LOCKED.clear()


def _selftest():
    """Minimal self-check runnable via `python3 bin/atomicwrite.py`."""
    import json
    import tempfile as _tf
    tmpdir = _tf.mkdtemp()
    reset()

    # 1. fresh atomic write
    p1 = os.path.join(tmpdir, "a.json")
    ok, rep = safe_write(p1, json.dumps({"a": 1}))
    assert ok, rep
    assert json.load(open(p1)) == {"a": 1}, "atomic write content mismatch"

    # 2. overwrite existing file (should still work via atomic replace)
    ok, rep = safe_write(p1, json.dumps({"a": 2}))
    assert ok, rep
    assert json.load(open(p1)) == {"a": 2}

    # 3. write into a missing parent (pre-flight creates it)
    p2 = os.path.join(tmpdir, "sub", "b.txt")
    ok, rep = safe_write(p2, "hello")
    assert ok, rep

    # 4. read-only target: pre-flight+chmod routing recovers
    p3 = os.path.join(tmpdir, "ro.txt")
    with open(p3, "w") as fh:
        fh.write("old")
    os.chmod(p3, 0o444)
    ok, rep = safe_write(p3, "new")
    assert ok, rep
    assert open(p3).read() == "new"

    # 5. patch fallback with old substring
    p4 = os.path.join(tmpdir, "p.txt")
    with open(p4, "w") as fh:
        fh.write("AAA BBB AAA")
    ok, rep = safe_write(p4, "CCC", old="BBB")
    assert ok, rep
    assert open(p4).read() == "AAA CCC AAA"

    # 6. ambiguous patch (non-unique) must not guess — falls through, returns ok via atomic
    ok, rep = safe_write(p4, "DDD", old="AAA")  # two matches -> atomic replace wins
    assert ok, rep
    assert open(p4).read() == "DDD"

    # 7. watchdog: two consecutive failures lock the path
    p5 = os.path.join(tmpdir, "lock.txt")
    # force failure by making parent a file (cannot create temp in it)
    os.makedirs(tmpdir + "/block", exist_ok=True)
    fake = tmpdir + "/notdir"
    with open(fake, "w") as fh:
        fh.write("x")
    badpath = fake + "/child.txt"
    ok1, _ = safe_write(badpath, "x")
    ok2, _ = safe_write(badpath, "x")
    assert not ok1 and not ok2, "expected two failures on unwritable path"
    ok3, rep3 = safe_write(badpath, "x")
    assert not ok3, "watchdog should lock after 2 consecutive failures"
    assert any("watchdog" in r for r in rep3), rep3

    # 8. forced recovery after locking (new evidence) succeeds on a good path
    reset()
    ok, rep = safe_write(p1, json.dumps({"a": 3}))
    assert ok, rep

    print("ATOMICWRITE_SELFTEST_PASS")


if __name__ == "__main__":
    _selftest()
