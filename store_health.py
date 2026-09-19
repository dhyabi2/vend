#!/usr/bin/env python3
"""Payment-store health probe.

`/health` on 2026-09-19 reported `status: ok` while every paid call answered 500
(`sqlite3.OperationalError: unable to open database file`). The endpoint probed
its upstreams and its modules but never the store it needs to take money, so a
green light hid a broken rail.

`check()` answers one question: can this process actually open the redemptions
store the way a paid call will? It opens the same path the live store uses
(`store.DB_PATH`), runs a trivial read against the `redemptions` table, and
closes again. It never creates anything in production beyond what `store.init()`
already does, and it never raises: a health probe that can crash is a health
probe that lies.
"""
from __future__ import annotations

import sqlite3


def check() -> tuple[bool, str]:
    """Return (healthy, detail). Never raises."""
    try:
        import store
        db_path = store.DB_PATH
    except Exception as exc:  # import failure is itself a diagnosis
        return False, f"store module unavailable: {type(exc).__name__}: {exc}"

    try:
        conn = sqlite3.connect(db_path, timeout=3)
    except Exception as exc:
        return False, f"error: cannot open {db_path} ({type(exc).__name__}: {exc})"

    try:
        row = conn.execute("SELECT COUNT(*) FROM redemptions").fetchone()
        count = int(row[0]) if row else 0
        return True, f"{db_path} readable, {count} redemption(s)"
    except Exception as exc:
        return False, (f"error: {db_path} opened but redemptions unreadable "
                       f"({type(exc).__name__}: {exc})")
    finally:
        try:
            conn.close()
        except Exception:
            pass
