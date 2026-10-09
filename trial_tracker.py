"""In-memory free trial tracker for Vend endpoints, and who it counts.

Tracks how many free calls each caller has made per rolling day.
Resets automatically — no DB, no state beyond process lifetime.
A server restart clears all counters, which is fine for a free trial.

The bucket a call is counted in is decided here too (``trial_bucket``),
because getting that wrong is the difference between a free sample and a
free service.  Two rules, each paid for by a measured leak (2026-10-09):

* ``X-Forwarded-For`` is only evidence when the request reached us through
  our own reverse proxy, and then only at the hop that proxy appended.
  Everything to the left of it was written by the caller.
* The bucket is a network prefix, not an address, so a caller arriving from
  a different address on every call is still one caller.
"""

import ipaddress
import os
import time
import threading
import logging

log = logging.getLogger("vend.trial")

# --- Config (env overridable) ---
_MAX_FREE_PER_CALLER = int(os.environ.get("VEND_FREE_TRIAL_LIMIT", "5"))
"""Max free (unpaid) calls per caller per rolling day."""

_TRIAL_WINDOW_SEC = 86_400  # 24 hours
"""Rolling window: calls older than this don't count."""

TRUSTED_PROXY_HOPS = int(os.environ.get("VEND_TRUSTED_PROXY_HOPS", "1"))
"""How many reverse proxies of ours sit in front of the app.

Vend runs behind one Caddy on the box, so the real client is the last
element Caddy appended to ``X-Forwarded-For`` — index ``-1``.  Raise this
only if another proxy of ours is added in front, never to accommodate a
caller's own header.
"""

_IPV4_TRIAL_PREFIX = 24
_IPV6_TRIAL_PREFIX = 48
"""A free sample is per caller.  A caller is a network, not an address.

A cloud NAT pool or an agent harness hands out addresses from a range; one
of ours was measured rotating inside ``160.79.106.0/24`` between two calls
a minute apart.  Keyed on the address, that pool collects ``limit`` free
calls per address it owns; keyed on the /24 it collects ``limit``.  IPv6
customers get a /48 or better, so the same reasoning gives /48 there.
"""

_UNIDENTIFIED = "unidentified"
"""The single shared bucket for calls we cannot place.

Fails closed on purpose: a caller that sends an unparseable address must
not thereby become a brand-new caller.  Everything unplaceable shares one
allowance, so garbage costs a payment instead of buying a free call.
"""


_DEFAULT_TRUSTED_PROXIES = "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7"
"""Where a reverse proxy of ours can be: loopback, RFC 1918, IPv6 ULA.

Spelled out rather than taken from ``ipaddress.is_private``, which also
answers True for the TEST-NET documentation ranges (``203.0.113.0/24``,
``198.51.100.0/24``, ``192.0.2.0/24``) and for ``192.0.0.0/24``.  A
predicate meaning "is this one of our own processes" must not quietly
include addresses that can appear on the public internet.  Override with
``VEND_TRUSTED_PROXIES`` as a comma-separated CIDR list.
"""


_proxy_network_cache: dict[str, list] = {}


def _trusted_proxy_networks():
    """The parsed allowlist, memoised on the raw env string.

    This is read on every paid call, so the CIDR parsing is done once per
    distinct setting rather than six times per request; keying the memo on
    the raw value keeps an env change in a test or a restart honoured.
    """
    raw = os.environ.get("VEND_TRUSTED_PROXIES", _DEFAULT_TRUSTED_PROXIES)
    cached = _proxy_network_cache.get(raw)
    if cached is not None:
        return cached
    nets = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            log.warning("TRIAL: ignoring unparseable VEND_TRUSTED_PROXIES entry %r", part)
    _proxy_network_cache[raw] = nets
    return nets


def _parse(host: str):
    """*host* as an address, with an IPv4-mapped IPv6 form unwrapped to IPv4.

    A dual-stack listener reports a v4 peer as ``::ffff:127.0.0.1``.  Left
    as a v6 address that form breaks both decisions at once: the loopback
    allowlist entry never matches it, so the proxy on the box stops being
    trusted, and every mapped address shares the single bucket ``::/48``.
    The first alone would collapse all of Vend's callers into one trial
    allowance.  Returns None if *host* is not an address at all.
    """
    try:
        addr = ipaddress.ip_address((host or "").strip())
    except ValueError:
        return None
    mapped = getattr(addr, "ipv4_mapped", None)
    return mapped or addr


def _is_trustworthy_peer(host: str) -> bool:
    """Is *host* one of our own processes, i.e. may its headers be believed?

    Only the reverse proxy on the box (and, in tests, a loopback client)
    is allowed to tell us who the caller is.  A request that arrived from
    anywhere else carries headers the caller chose.
    """
    addr = _parse(host)
    if addr is None:
        return False
    return any(addr in net for net in _trusted_proxy_networks()
               if net.version == addr.version)


def client_address(peer: str | None, forwarded_for: str = "",
                   real_ip: str = "", hops: int | None = None) -> str:
    """The caller's address, believing a header only where that is sound.

    *peer* is the address the connection actually came from.  When that is
    not one of our own proxies, it IS the answer and the headers are
    ignored.  When it is, the client is the element ``hops`` from the right
    of ``X-Forwarded-For`` — the one our proxy wrote — falling back to
    ``X-Real-IP`` and then to the peer itself.
    """
    if hops is None:
        hops = TRUSTED_PROXY_HOPS
    peer = (peer or "").strip()
    if not _is_trustworthy_peer(peer):
        return peer or _UNIDENTIFIED

    chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    if chain:
        # hops=1 -> chain[-1], the address our own proxy appended.  A chain
        # shorter than the configured depth means something upstream did not
        # append what we expect, so take the leftmost rather than inventing
        # a hop; it is the most trustworthy element available.
        index = max(0, len(chain) - max(1, hops))
        return chain[index]

    return (real_ip or "").strip() or peer


def trial_bucket(address: str) -> str:
    """The free-trial counter *address* belongs to.

    A /24 for IPv4 and a /48 for IPv6, so one caller arriving from many
    addresses is counted once.  Anything unparseable shares one bucket.
    """
    addr = _parse(address)
    if addr is None:
        return _UNIDENTIFIED
    prefix = _IPV4_TRIAL_PREFIX if addr.version == 4 else _IPV6_TRIAL_PREFIX
    return str(ipaddress.ip_network(f"{addr}/{prefix}", strict=False))


class TrialTracker:
    """Track free trial usage per caller bucket (see ``trial_bucket``).

    Thread-safe (all public methods hold a lock).  Each bucket's history is
    a list of Unix timestamps; calls older than *window_sec* are pruned on
    every access so the limit is a rolling window rather than a calendar
    day.

    The *ip* arguments are whatever key the caller counts by; ``server.py``
    passes ``trial_bucket(client_address(...))``.
    """

    def __init__(self, max_free: int = _MAX_FREE_PER_CALLER, window_sec: int = _TRIAL_WINDOW_SEC):
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