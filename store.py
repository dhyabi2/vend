"""Durable one-time-use registry for Nano payment blocks.

Every redeemed block hash is recorded in SQLite with a UNIQUE constraint before
the paid work runs.  An INSERT hitting that constraint is a replay: the caller
is refused 402 and no extraction runs.

Thread-safe within the process via a module-level lock; process-safe via SQLite
PRIMARY KEY (same mechanism).

Schema
------
CREATE TABLE redemptions (
    block_hash  TEXT PRIMARY KEY,      -- Nano block hash (64 uppercase hex)
    amount_raw  TEXT,                  -- amount redeemed (raw)
    source      TEXT,                  -- sending account
    endpoint    TEXT,                  -- which endpoint was called
    status      TEXT NOT NULL DEFAULT 'claimed',  -- claimed / delivered / failed
    created_at  TEXT NOT NULL           -- ISO-8601 timestamp
)
"""

import os
import sqlite3
import threading
import datetime

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("VEND_DB", os.path.join(MODULE_DIR, "state", "vend.sqlite3"))

_lock = threading.Lock()

# ── helpers ──────────────────────────────────────────────────────────────


def _ensure_dir(path: str):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _connect():
    """Open a connection to the DB (WAL mode, busy timeout)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_INIT_DONE = False


def init():
    """Ensure the redemptions table exists. Safe to call repeatedly."""
    global _INIT_DONE
    if _INIT_DONE:
        return
    with _lock:
        if _INIT_DONE:
            return
        _ensure_dir(DB_PATH)
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS redemptions (
                    block_hash  TEXT PRIMARY KEY,
                    amount_raw  TEXT,
                    source      TEXT,
                    endpoint    TEXT,
                    status      TEXT NOT NULL DEFAULT 'claimed',
                    created_at  TEXT NOT NULL
                )
                """
            )
            conn.commit()
            _INIT_DONE = True
        finally:
            conn.close()

# ── public API ───────────────────────────────────────────────────────────


def redeem(
    block_hash: str,
    endpoint: str = "",
    amount_raw: str = "",
    source: str = "",
) -> bool:
    """Atomically record *block_hash* as claimed.

    Returns ``True`` if this is the first call (proceed with paid work).
    Returns ``False`` if the block was already spent on *any* previous call.
    """
    init()
    with _lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO redemptions "
                    "(block_hash, amount_raw, source, endpoint, status, created_at) "
                    "VALUES (?, ?, ?, ?, 'claimed', ?)",
                    (block_hash, amount_raw, source, endpoint, _now()),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()


def status_of(block_hash: str) -> str | None:
    """Return the stored status of *block_hash*, or ``None`` if unknown."""
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT status FROM redemptions WHERE block_hash = ?", (block_hash,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def resolve(block_hash: str, status: str):
    """Mark *block_hash* as *status* (``'delivered'`` | ``'failed'``).

    Called **after** the paid work completes (or fails).
    """
    init()
    conn = _connect()
    try:
        conn.execute(
            "UPDATE redemptions SET status = ?, created_at = ? WHERE block_hash = ?",
            (status, _now(), block_hash),
        )
        conn.commit()
    finally:
        conn.close()


def count_redeemed() -> int:
    """Total redeemed blocks (the number of paid calls handled so far)."""
    init()
    conn = _connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM redemptions")
        return cur.fetchone()[0]
    finally:
        conn.close()


def count_distinct_payers() -> int:
    """Distinct Nano accounts that have paid at least once."""
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT COUNT(DISTINCT source) FROM redemptions WHERE source != ''"
        )
        return cur.fetchone()[0]
    finally:
        conn.close()