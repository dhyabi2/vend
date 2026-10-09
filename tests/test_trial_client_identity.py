"""Who the free trial thinks you are decides whether Vend ever gets paid.

Found 2026-10-09 against the live endpoint while clearing the gate on
``Haustorium12/gold-402#284``.  That directory's maintainer had measured
``/api/v1/extract`` serving **200 free across 17 calls** where the gate bot
had measured the documented 402, and the contradiction was neither a flake
nor a deploy: both are what the code does, to two different callers.

Two separate holes, both in how ``require_payment`` decides which trial
bucket a call belongs to:

1. **The caller names itself.**  The client address was read from the
   *leftmost* element of ``X-Forwarded-For`` whenever that header was
   present, with no check that the request actually arrived through our
   own reverse proxy.  On a direct connection the header is just input, so
   one line of it buys a fresh five-call allowance -- and a different line
   buys another.  The paywall is then decorative.

2. **A rotating egress gets one allowance per address.**  Keyed on the
   exact address, a caller behind a NAT pool collects five free calls per
   source address.  Measured from this session on 2026-10-09: two calls a
   minute apart arrived from ``160.79.106.129`` and ``160.79.106.130`` and
   ``trial_remaining`` went *up*, 3 then 4.  That population -- agents
   behind a proxy or a cloud NAT -- is exactly who Vend advertises to.

So the laws below: a header is believed only from a trusted peer and only
at the hop that peer appended, and the bucket is a network prefix, not an
address.  The controls at the end must hold either way -- a naked x402
probe still gets its challenge, and a genuine first-time caller still gets
its free sample.

Run: python3 -m pytest tests/test_trial_client_identity.py -v
"""

import os
import sys
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
import store
from trial_tracker import reset_tracker_for_testing

# A page body the extractor never has to go online for.
EXTRACTED = {"url": "https://example.com", "title": "Example Domain",
             "text": "t", "markdown": "t", "error": None}

UNTRUSTED_PEER = ("203.0.113.9", 54321)   # a caller talking straight to us
PROXY_PEER = ("127.0.0.1", 54321)         # Caddy, on the box


@pytest.fixture(autouse=True)
def fresh_trial_counters():
    """Each law starts from an empty tracker and its own redemption store."""
    reset_tracker_for_testing()
    path = tempfile.mktemp(suffix=".sqlite3")
    old_path, old_init = store.DB_PATH, store._INIT_DONE
    store.DB_PATH, store._INIT_DONE = path, False
    store.init()
    try:
        yield
    finally:
        store.DB_PATH, store._INIT_DONE = old_path, old_init
        reset_tracker_for_testing()


def _client(peer):
    return TestClient(server.app, client=peer)


def _extract(client, headers=None):
    """One real (parameter-carrying) call to the cheapest paid endpoint."""
    with patch("server.extract_url", return_value=dict(EXTRACTED)):
        return client.get("/api/v1/extract?url=https://example.com",
                          headers=headers or {})


def _served_free(resp):
    """Did this call get real data without paying?"""
    if resp.status_code != 200:
        return False
    return bool((resp.json().get("payment") or {}).get("free_trial"))


# ── The defect ────────────────────────────────────────────────────────


def test_a_direct_caller_cannot_mint_allowances_with_its_own_header():
    """X-Forwarded-For from an untrusted peer is input, not identity.

    Five free calls, then the sixth must be a 402 however the caller
    labels itself.  Before the fix each new label was a new bucket, so
    the endpoint served free forever to anyone who sent the header.
    """
    c = _client(UNTRUSTED_PEER)
    for i in range(5):
        r = _extract(c, {"X-Forwarded-For": f"10.1.1.{i}"})
        assert _served_free(r), f"call {i + 1} should be the free sample, got {r.status_code}"

    r = _extract(c, {"X-Forwarded-For": "10.9.9.9"})
    assert r.status_code == 402, (
        "a relabelled caller got a sixth free call: the trial is unlimited "
        f"to anyone who sets one header (got {r.status_code})"
    )


def test_the_hop_that_counts_is_the_one_the_proxy_appended():
    """Through Caddy, only the rightmost element is ours; the rest is input.

    The caller prepends whatever it likes; Caddy appends the address it
    actually saw.  Reading the leftmost element hands the caller the key
    again, one indirection further on.
    """
    c = _client(PROXY_PEER)
    for i in range(5):
        r = _extract(c, {"X-Forwarded-For": f"10.2.2.{i}, 198.51.100.7"})
        assert _served_free(r), f"call {i + 1} should be the free sample, got {r.status_code}"

    r = _extract(c, {"X-Forwarded-For": "10.2.2.99, 198.51.100.7"})
    assert r.status_code == 402, (
        "the spoofable leftmost hop was used as the identity, so a caller "
        f"behind our own proxy can still mint allowances (got {r.status_code})"
    )


def test_one_rotating_egress_pool_shares_one_allowance():
    """The measured case: 160.79.106.129 and .130 are one caller.

    A free sample is per caller, and a caller that reaches us from a
    different address on every call is still one caller.  A /24 is the
    smallest unit that holds a NAT pool together.
    """
    c = _client(PROXY_PEER)
    for i in range(5):
        r = _extract(c, {"X-Forwarded-For": f"160.79.106.{129 + i}"})
        assert _served_free(r), f"call {i + 1} should be the free sample, got {r.status_code}"

    r = _extract(c, {"X-Forwarded-For": "160.79.106.200"})
    assert r.status_code == 402, (
        "a rotating egress pool collected a sixth free call: five per source "
        f"address is five times the pool size, not five (got {r.status_code})"
    )


def test_an_ipv6_caller_is_grouped_by_its_site_prefix():
    """IPv6 hands out /64s and /48s per customer, not single addresses.

    Keyed on the full 128 bits, one IPv6 caller has more free trials than
    there are atoms worth counting.
    """
    c = _client(PROXY_PEER)
    for i in range(5):
        r = _extract(c, {"X-Forwarded-For": f"2001:db8:1:{i}::1"})
        assert _served_free(r), f"call {i + 1} should be the free sample, got {r.status_code}"

    r = _extract(c, {"X-Forwarded-For": "2001:db8:1:ffff::9"})
    assert r.status_code == 402, (
        "an IPv6 caller got a sixth free call from the same /48 "
        f"(got {r.status_code})"
    )


def test_an_unparseable_address_cannot_be_a_fresh_bucket():
    """Garbage in the header must not read as a brand-new caller.

    Fail closed: everything we cannot identify shares one allowance, so a
    nonsense value costs the caller a payment rather than buying one.
    """
    c = _client(PROXY_PEER)
    for i in range(5):
        r = _extract(c, {"X-Forwarded-For": f"not-an-address-{i}"})
        assert _served_free(r), f"call {i + 1} should be the free sample, got {r.status_code}"

    r = _extract(c, {"X-Forwarded-For": "also-not-an-address"})
    assert r.status_code == 402, (
        f"unidentifiable callers each got their own allowance (got {r.status_code})"
    )


# ── Controls: the refusal must not cost a good call ───────────────────


def test_a_naked_x402_probe_still_gets_its_challenge():
    """x402scan and the CDP Bazaar require a 402 on a bare probe."""
    c = _client(PROXY_PEER)
    r = c.get("/api/v1/extract", headers={"X-Forwarded-For": "160.79.106.129"})
    assert r.status_code == 402
    body = r.json()
    assert body["error"] == "payment_required"
    # The challenge's shape, not its configuration: VEND_ACCOUNT is unset in
    # a test process, so pay_to is empty here and the live account on the box.
    assert "pay_to" in body and "price_xno" in body


def test_a_first_time_caller_still_gets_its_free_sample():
    """The trial still exists; this is a narrowing, not a removal."""
    c = _client(PROXY_PEER)
    r = _extract(c, {"X-Forwarded-For": "198.51.100.23"})
    assert _served_free(r)
    payment = r.json()["payment"]
    assert payment["trial_remaining"] == 4
    assert payment["trial_limit"] == 5
    assert r.headers["X-Trial-Remaining"] == "4"


def test_two_genuinely_different_networks_keep_separate_allowances():
    """Narrowing to a prefix must not collapse the whole internet into one."""
    c = _client(PROXY_PEER)
    for i in range(5):
        assert _served_free(_extract(c, {"X-Forwarded-For": f"160.79.106.{129 + i}"}))
    assert _extract(c, {"X-Forwarded-For": "160.79.106.200"}).status_code == 402

    # A different /24 is a different caller and still has its sample.
    assert _served_free(_extract(c, {"X-Forwarded-For": "203.0.113.4"}))


def test_a_trial_call_never_claims_a_payment_it_did_not_take():
    """The receipt has to say 'trial', or the buyer cannot audit us."""
    c = _client(PROXY_PEER)
    r = _extract(c, {"X-Forwarded-For": "198.51.100.77"})
    payment = r.json()["payment"]
    assert payment["free_trial"] is True
    assert payment["amount_xno"] == "0.000000"
    assert payment["block_hash"].startswith("trial-")
    assert r.json()["receipt"].startswith("paid-by-trial")


def test_a_direct_caller_with_no_header_is_still_identified_by_its_peer():
    """No header at all is the ordinary case and must keep working."""
    c = _client(UNTRUSTED_PEER)
    for i in range(5):
        assert _served_free(_extract(c)), f"call {i + 1} should be the free sample"
    assert _extract(c).status_code == 402


# ── The two decisions, at unit level ─────────────────────────────────


from trial_tracker import client_address, trial_bucket  # noqa: E402


@pytest.mark.parametrize("peer,xff,real,expected", [
    # An untrusted peer IS the client; its headers are ignored entirely.
    ("8.8.8.8", "1.2.3.4", "5.6.7.8", "8.8.8.8"),
    ("160.79.106.129", "10.0.0.1, 10.0.0.2", "", "160.79.106.129"),
    # Behind our own proxy, the hop the proxy appended is the client.
    ("127.0.0.1", "1.2.3.4, 160.79.106.129", "", "160.79.106.129"),
    ("10.0.0.3", "1.2.3.4, 160.79.106.129", "", "160.79.106.129"),
    ("127.0.0.1", "160.79.106.129", "", "160.79.106.129"),
    # No chain: X-Real-IP, then the peer.
    ("127.0.0.1", "", "9.9.9.9", "9.9.9.9"),
    ("127.0.0.1", "", "", "127.0.0.1"),
    # Whitespace and empty elements in the chain are not hops.
    ("127.0.0.1", " 1.2.3.4 , , 160.79.106.129 ", "", "160.79.106.129"),
    # A peer we cannot even parse is not a proxy of ours.
    ("testclient", "1.2.3.4", "", "testclient"),
    ("", "1.2.3.4", "", "unidentified"),
])
def test_client_address_believes_a_header_only_where_that_is_sound(peer, xff, real, expected):
    assert client_address(peer, xff, real) == expected


def test_a_chain_shorter_than_the_configured_depth_takes_the_leftmost():
    """Two proxies configured, one hop present: do not invent the missing one.

    Indexing ``-hops`` into a short chain would wrap around and read the
    caller's own element as ours.  The leftmost is the most trustworthy
    thing actually present.
    """
    assert client_address("127.0.0.1", "160.79.106.129", hops=2) == "160.79.106.129"
    assert client_address("127.0.0.1", "1.2.3.4, 160.79.106.129", hops=2) == "1.2.3.4"
    assert client_address("127.0.0.1", "1.2.3.4, 5.6.7.8, 160.79.106.129", hops=2) == "5.6.7.8"
    # Two hops short of the configured depth: ``len(chain) - hops`` is
    # negative here and would index from the right, reading the innermost
    # proxy as the client and bucketing the whole internet together.
    assert client_address("127.0.0.1", "1.2.3.4, 160.79.106.129", hops=3) == "1.2.3.4"
    assert client_address("127.0.0.1", "1.2.3.4, 5.6.7.8, 160.79.106.129", hops=9) == "1.2.3.4"


@pytest.mark.parametrize("address,expected", [
    ("160.79.106.129", "160.79.106.0/24"),
    ("160.79.106.130", "160.79.106.0/24"),
    ("160.79.106.255", "160.79.106.0/24"),
    ("160.79.107.1", "160.79.107.0/24"),
    ("2001:db8:1:5::9", "2001:db8:1::/48"),
    ("2001:db8:1:ffff::1", "2001:db8:1::/48"),
    ("2001:db8:2::1", "2001:db8:2::/48"),
    ("not-an-address", "unidentified"),
    ("", "unidentified"),
    ("160.79.106.129, 1.2.3.4", "unidentified"),
])
def test_trial_bucket_groups_a_caller_by_its_network(address, expected):
    assert trial_bucket(address) == expected


def test_an_untrusted_peer_cannot_be_promoted_by_a_documentation_range():
    """``ipaddress.is_private`` is True for TEST-NET; the allowlist is not.

    203.0.113.0/24, 198.51.100.0/24 and 192.0.2.0/24 are reserved for
    documentation but are ordinary routable-looking addresses as far as a
    trust decision goes.  Reading "one of ours" as ``is_private`` would
    have let a peer in any of them name its own client.
    """
    for peer in ("203.0.113.9", "198.51.100.7", "192.0.2.1", "100.64.0.1"):
        assert client_address(peer, "10.1.1.1") == peer, peer
    for peer in ("127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "fd00::1"):
        assert client_address(peer, "10.1.1.1") == "10.1.1.1", peer


def test_a_dual_stack_listener_reports_v4_peers_as_ipv4_mapped():
    """``::ffff:127.0.0.1`` is the proxy on the box, and ``::ffff:a.b.c.d`` is one caller.

    Left unwrapped, the mapped form fails the loopback allowlist (so Caddy
    stops being trusted and every caller behind it collapses into the one
    peer bucket) and every mapped address shares ``::/48``.  Both are the
    whole-site failure mode, not a narrow one.
    """
    from trial_tracker import _is_trustworthy_peer

    assert _is_trustworthy_peer("::ffff:127.0.0.1")
    assert _is_trustworthy_peer("::ffff:10.0.0.4")
    assert not _is_trustworthy_peer("::ffff:8.8.8.8")
    assert client_address("::ffff:127.0.0.1", "1.2.3.4, 160.79.106.129") == "160.79.106.129"
    assert trial_bucket("::ffff:160.79.106.129") == "160.79.106.0/24"
    assert trial_bucket("::ffff:160.79.107.1") == "160.79.107.0/24"
    # A genuine IPv6 address is still grouped as IPv6.
    assert trial_bucket("2001:db8:1:5::9") == "2001:db8:1::/48"


def test_the_trusted_proxy_allowlist_is_configurable_and_fails_closed():
    """A deployment behind a proxy on a public address can name it.

    An unparseable entry is dropped with a warning rather than taken as a
    wildcard, and an allowlist that parses to nothing trusts nobody.
    """
    old = os.environ.get("VEND_TRUSTED_PROXIES")
    try:
        os.environ["VEND_TRUSTED_PROXIES"] = "160.79.106.0/24, nonsense/99"
        from trial_tracker import _is_trustworthy_peer
        assert _is_trustworthy_peer("160.79.106.5")
        assert not _is_trustworthy_peer("127.0.0.1")   # no longer listed
        assert client_address("160.79.106.5", "1.2.3.4, 8.8.8.8") == "8.8.8.8"

        os.environ["VEND_TRUSTED_PROXIES"] = "   "
        assert not _is_trustworthy_peer("127.0.0.1")
        assert client_address("127.0.0.1", "1.2.3.4") == "127.0.0.1"
    finally:
        if old is None:
            os.environ.pop("VEND_TRUSTED_PROXIES", None)
        else:
            os.environ["VEND_TRUSTED_PROXIES"] = old
