#!/usr/bin/env python3
"""Merge what the swarm's members did into the lead's journal, so there is ONE map and ONE Newsletter voice.

Each member journals into its own private /root, which keeps thirteen writers off one file and keeps a member
from editing another's record. But the live map at www.vend-agent.xyz and the 06:10 Newsletter both read
the LEAD's journal - without this, twelve agents' work would be invisible.

Only what a person would want to see is carried over: conversations, status lines, commits, runs, corrections.
Heartbeats, tool calls and model calls stay where they are: thirteen agents produce ~180,000 of those a day,
which would push the lead's own facts out of a 300,000-row journal in under two days (the retention trap that
already destroyed an issue once, 2026-09-15). Every merged fact carries `member`.
Runs from cron as root on the host; members cannot reach the lead's journal at all.
"""
import glob
import json
import os
import sqlite3
import sys
import time
from importlib.machinery import SourceFileLoader

BASE = os.environ.get("RAI_SWARM_BASE", "/srv/vend-swarm")
LEAD_JOURNAL = os.environ.get("NANO_PULSE_DB", "/root/.hermes/nano-pulse/journal.db")
JOURNAL_LIB = os.environ.get("RAI_JOURNAL_LIB", "/root/.hermes/plugins/nano-pulse/journal.py")
STATE = os.environ.get("RAI_MERGE_STATE", os.path.join(BASE, "merge-state.json"))
KEEP = {"status", "bridge", "commit", "run", "correction", "distribution", "scope", "tests", "law", "block"}
BATCH = 500


def merge(base=BASE, lead_journal=LEAD_JOURNAL, state_path=STATE, lib=JOURNAL_LIB):
    journal = SourceFileLoader("swarm_merge_journal", lib).load_module()
    try:
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        state = {}
    moved, lead = {}, None
    for path in sorted(glob.glob(os.path.join(base, "*", "root", ".hermes", "nano-pulse", "journal.db"))):
        member = path.split(os.sep)[-5]
        try:
            src = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
            rows = src.execute("SELECT seq, ts, kind, data FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
                               (int(state.get(member, 0)), BATCH * 20)).fetchall()
            src.close()
        except sqlite3.Error:
            continue                      # not journalled yet, or mid-write: next minute
        out, last = [], state.get(member, 0)
        for seq, ts, kind, data in rows:
            last = seq
            if kind not in KEEP:
                continue
            try:
                d = json.loads(data)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            d["member"] = member
            if kind == "status" and isinstance(d.get("text"), str) and not d["text"].startswith(member):
                d["text"] = f"{member}: {d['text']}"
            out.append((ts, kind, d))
        if out:
            lead = lead or journal.connect(lead_journal)
            for i in range(0, len(out), BATCH):
                journal.append(lead, out[i:i + BATCH])
        state[member] = last              # only after the append returned: a crash repeats a batch, never drops one
        moved[member] = len(out)
    if lead is not None:
        lead.close()
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, state_path)
    return moved


if __name__ == "__main__":
    t0 = time.time()
    moved = merge()
    if any(moved.values()) or "-v" in sys.argv:
        print(f"{time.strftime('%FT%TZ', time.gmtime())} merged {sum(moved.values())} facts "
              f"({', '.join(f'{m}:{n}' for m, n in moved.items() if n)}) in {time.time() - t0:.2f}s")
