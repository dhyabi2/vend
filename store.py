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

CREATE TABLE IF NOT EXISTS balances (
    account     TEXT PRIMARY KEY,       -- Nano account (nano_...)
    balance_raw TEXT NOT NULL DEFAULT '0',  -- current balance in raw
    total_topup_raw TEXT NOT NULL DEFAULT '0',  -- lifetime topups in raw
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)

CREATE TABLE IF NOT EXISTS balance_topups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account     TEXT NOT NULL,
    amount_raw  TEXT NOT NULL,
    block_hash  TEXT NOT NULL UNIQUE,   -- the Nano block that funded this topup
    created_at  TEXT NOT NULL
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
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_INIT_DONE = False


def init():
    """Ensure all tables exist. Safe to call repeatedly."""
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS balances (
                    account     TEXT PRIMARY KEY,
                    balance_raw TEXT NOT NULL DEFAULT '0',
                    total_topup_raw TEXT NOT NULL DEFAULT '0',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS balance_topups (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    account     TEXT NOT NULL,
                    amount_raw  TEXT NOT NULL,
                    block_hash  TEXT NOT NULL UNIQUE,
                    created_at  TEXT NOT NULL
                )
                """
            )
            conn.commit()
            _INIT_DONE = True
        finally:
            conn.close()


# ── redemption API ──────────────────────────────────────────────────────


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
        return row["status"] if row else None
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


def get_redemption(block_hash: str) -> dict | None:
    """Return full redemption record for *block_hash*, or None if unknown.

    Returns a dict with keys: block_hash, amount_raw, source, endpoint, status, created_at.
    Block hashes are hex and case-insensitive, so the lookup normalises to
    upper case — a buyer who queries their paid block in lower case must not
    get a 404 when the redemption exists (hit live: paid block stored upper,
    buyer queried lower -> 'No payment found').
    """
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT block_hash, amount_raw, source, endpoint, status, created_at "
            "FROM redemptions WHERE UPPER(block_hash) = ?",
            (block_hash.upper(),),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)
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


# ── balance / prepaid API ──────────────────────────────────────────────


def top_up(block_hash: str, account: str, amount_raw: str) -> bool:
    """Credit *account* with *amount_raw* from a verified on-chain payment.

    The *block_hash* is recorded with a UNIQUE constraint so a single payment
    cannot be split into multiple top-ups.  Returns True if the credit was
    applied, False if this block_hash was already used for a top-up.
    """
    init()
    now = _now()
    with _lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")

            # Record this top-up transaction
            try:
                conn.execute(
                    "INSERT INTO balance_topups "
                    "(account, amount_raw, block_hash, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (account, amount_raw, block_hash, now),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False  # duplicate top-up block

            # Upsert the balance
            existing = conn.execute(
                "SELECT balance_raw, total_topup_raw FROM balances WHERE account = ?",
                (account,),
            ).fetchone()
            if existing:
                new_balance = str(int(existing["balance_raw"]) + int(amount_raw))
                new_total_topup = str(
                    int(existing["total_topup_raw"]) + int(amount_raw)
                )
                conn.execute(
                    "UPDATE balances SET balance_raw = ?, total_topup_raw = ?, updated_at = ? "
                    "WHERE account = ?",
                    (new_balance, new_total_topup, now, account),
                )
            else:
                conn.execute(
                    "INSERT INTO balances (account, balance_raw, total_topup_raw, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (account, amount_raw, amount_raw, now, now),
                )

            conn.execute("COMMIT")
            return True
        finally:
            conn.close()


def balance_of(account: str) -> int:
    """Return the current balance of *account* in raw, or 0 if unknown."""
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT balance_raw FROM balances WHERE account = ?", (account,)
        )
        row = cur.fetchone()
        return int(row["balance_raw"]) if row else 0
    finally:
        conn.close()


def deduct_balance(account: str, amount_raw: str) -> bool:
    """Deduct *amount_raw* from *account*'s balance.

    Returns True if the deduction succeeded, False if insufficient funds.
    """
    init()
    now = _now()
    with _lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "SELECT balance_raw FROM balances WHERE account = ?", (account,)
            )
            row = cur.fetchone()
            if not row:
                conn.execute("ROLLBACK")
                return False
            current = int(row["balance_raw"])
            needed = int(amount_raw)
            if current < needed:
                conn.execute("ROLLBACK")
                return False
            new_balance = str(current - needed)
            conn.execute(
                "UPDATE balances SET balance_raw = ?, updated_at = ? WHERE account = ?",
                (new_balance, now, account),
            )
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()


def get_topup_history(account: str, limit: int = 10) -> list[dict]:
    """Return recent top-up transactions for *account*."""
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT amount_raw, block_hash, created_at FROM balance_topups "
            "WHERE account = ? ORDER BY id DESC LIMIT ?",
            (account, limit),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_balances() -> list[dict]:
    """Return all accounts with non-zero balances (for admin/monitoring)."""
    init()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT account, balance_raw, total_topup_raw, updated_at FROM balances"
        )
        rows = [dict(row) for row in cur.fetchall()]
        # Sort by balance_raw descending (sort first by string length, then by value)
        # This handles raw amounts above 2^63 that overflow SQLite INTEGER
        rows.sort(
            key=lambda r: (len(str(r["balance_raw"])), int(str(r["balance_raw"]))),
            reverse=True,
        )
        return rows
    finally:
        conn.close()