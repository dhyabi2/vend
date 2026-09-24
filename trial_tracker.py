"""In-memory free trial tracker for Vend endpoints.

Tracks how many free calls each IP has made per rolling day.
Resets automatically — no DB, no state beyond process lifetime.
A server restart clears all counters, which is fine for a free trial.
"""

import time
import threading
import logging

log = logging.getLogger("vend.trial")

# --- Config (env overridable) ---
_MAX_FREE_PER_IP = int(__import__("os").environ.get("VEND_FREE_TRIAL_LIMIT", "5"))
"""Max free (unpaid) calls per IP address per rolling day."""

_TRIAL_WINDOW_SEC = 86_400  # 24 hours
"""Rolling window: calls older than this don't count."""


class TrialTracker:
    """Track free trial usage per IP address.

    Thread-safe (all public methods hold a lock).  Each IP's history is a
    deque of Unix timestamps; calls older than *window_sec* are pruned on
    every access so the limit is a rolling window rather than a calendar
    day.
    """

    def __init__(self, max_free: int = _MAX_FREE_PER_IP, window_sec: int = _TRIAL_WINDOW_SEC):
        self.max_free = max_free
        self.window_sec = window_sec
        self._lock = threading.Lock()
        self._ips: dict[str, list[float]] = {}

    def remaining(self, ip: str) -> int:
        """How many free calls *ip* can still make right now."""
        now = time.time()
        with self._lock:
            history = self._ips.get(ip, [])
            # Prune older than the window
            cutoff = now - self.window_sec
            fresh = [t for t in history if t > cutoff]
            self._ips[ip] = fresh
            return max(0, self.max_free - len(fresh))

    def consume(self, ip: str) -> bool:
        """Try to consume one free trial slot for *ip*.

        Returns True if the slot was available and consumed; False if
        the IP is over its limit.
        """
        now = time.time()
        with self._lock:
            history = self._ips.get(ip, [])
            cutoff = now - self.window_sec
            fresh = [t for t in history if t > cutoff]
            if len(fresh) >= self.max_free:
                self._ips[ip] = fresh
                return False
            fresh.append(now)
            self._ips[ip] = fresh
            return True


# Module-level singleton so both server.py and tests see the same tracker
_tracker: TrialTracker | None = None


def get_tracker() -> TrialTracker:
    global _tracker
    if _tracker is None:
        _tracker = TrialTracker()
    return _tracker


def reset_tracker_for_testing():
    """Replace the singleton with a fresh one (test isolation)."""
    global _tracker
    _tracker = TrialTracker()