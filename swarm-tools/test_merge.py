#!/usr/bin/env python3
"""Laws for the journal merger. It writes to the LEAD's journal, so the first law is that the test cannot."""
import json, os, sqlite3, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import merge_journals as M

LIB = os.path.join(tempfile.mkdtemp(), "journal.py")
open(LIB, "w").write('''
import sqlite3, json
def connect(path):
    db = sqlite3.connect(path); db.execute("CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, data TEXT)"); return db
def append(db, rows):
    db.executemany("INSERT INTO events(ts,kind,data) VALUES (?,?,?)", [(t, k, json.dumps(d)) for t, k, d in rows]); db.commit()
''')


def member_journal(base, name, rows):
    d = os.path.join(base, name, "root", ".hermes", "nano-pulse"); os.makedirs(d)
    db = sqlite3.connect(os.path.join(d, "journal.db"))
    db.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, data TEXT)")
    db.executemany("INSERT INTO events(ts,kind,data) VALUES (?,?,?)", [(t, k, json.dumps(v)) for t, k, v in rows]); db.commit(); db.close()


def test():
    base = tempfile.mkdtemp(); lead = os.path.join(base, "lead.db"); state = os.path.join(base, "state.json")
    assert lead != M.LEAD_JOURNAL, "this test must never be able to reach the live journal"
    member_journal(base, "atlas", [(1.0, "heartbeat", {}), (2.0, "status", {"text": "crawling the a2a registry"}),
                                   (3.0, "tool", {"name": "curl"}), (4.0, "bridge", {"event": "seen", "agent": "orbit"})])
    member_journal(base, "beacon", [(5.0, "status", {"text": "beacon: already prefixed"}), (6.0, "llm_call", {})])
    moved = M.merge(base, lead, state, LIB)
    assert moved == {"atlas": 2, "beacon": 1}, moved
    rows = [(k, json.loads(d)) for k, d in sqlite3.connect(lead).execute("SELECT kind, data FROM events ORDER BY seq")]
    assert [k for k, _ in rows] == ["status", "bridge", "status"], "heartbeats, tool and model calls never cross"
    assert all(d["member"] in ("atlas", "beacon") for _, d in rows), "every merged fact says whose it is"
    assert rows[0][1]["text"] == "atlas: crawling the a2a registry" and rows[2][1]["text"] == "beacon: already prefixed"
    assert M.merge(base, lead, state, LIB) == {"atlas": 0, "beacon": 0}, "a second pass moves nothing twice"
    assert sqlite3.connect(lead).execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
    print("PASS merge: only facts a person would read cross into the lead's journal, each carrying its member, "
          "a status line names its author once, and nothing is ever merged twice")


if __name__ == "__main__":
    test()
