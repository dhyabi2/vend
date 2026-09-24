#!/usr/bin/env python3
"""Laws for vend-bridge: the record of Unstuck's conversation with agents from outside the Nano world.

Run: python3 vend/bridge/test_bridge.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["RAI_BRIDGE_DB"] = os.path.join(tempfile.mkdtemp(), "bridge.db")
os.environ["RAI_FIRST_CONTACT_CAP"] = "1000"  # the older laws open many; the cap has its own law, which pins 2
os.environ.setdefault("NANO_PULSE_LIB", os.path.join(tempfile.mkdtemp(), "no-plugins"))  # emit is best-effort, never required
import bridge as B  # noqa: E402


def refused(fn, needle):
    try:
        fn()
    except B.Refused as ex:
        assert needle in str(ex), (needle, str(ex))
        return str(ex)
    raise AssertionError(f"not refused: {needle}")


def test_bridge():
    db = B.connect(os.environ["RAI_BRIDGE_DB"])

    # The whole point of the agent: an outside agent that pays in something else today.
    out = B.seen(db, "clipper", "https://clipper.example.com/agent", "usdc", note="found on an x402 index", now=1000)
    assert out == {"agent": "clipper", "source": "https://clipper.example.com/agent", "pays_in": "usdc"}, out

    reasons = [
        # Measured 2026-09-18: all 11 of the first starters went to Nano-native services. Eleven tips, zero
        # conversions. An agent that already takes Nano is not a target, so the record refuses to call it one.
        refused(lambda: B.seen(db, "subnano", "https://subnano.me", "nano"), "already takes Nano"),
        refused(lambda: B.seen(db, "subnano", "https://subnano.me", "xno"), "already takes Nano"),
        refused(lambda: B.seen(db, "x", "https://x.example.com", "gold"), "--pays-in must be one of"),
        # "I publish my own denominator": a conversion nobody can check is not evidence.
        refused(lambda: B.seen(db, "y", "http://insecure.example.com", "usdc"), "public https URL"),
        refused(lambda: B.seen(db, "", "https://a.example.com", "usdc"), "--agent is required"),
        refused(lambda: B.said_unknown(db) if hasattr(B, "said_unknown") else B.message(db, "ghost", "hi", "out"), "is not recorded yet"),
        refused(lambda: B.set_status(db, "clipper", "famous"), "--status must be one of"),
        refused(lambda: B.message(db, "clipper", "", "out"), "--text is required"),
        refused(lambda: B.agreed(db, "clipper", ""), "--summary is required"),
    ]

    # A conversation: what we said, what it answered. The first answer moves it off "contacted" by itself —
    # an agent that replied is further along than one that only received a message, and nobody should have to say so.
    B.message(db, "clipper", "Nano moves instantly and costs nothing to receive. Want to try it?", "out", now=1001)
    assert B._status_of(db, "clipper") == "contacted"
    B.message(db, "clipper", "\u201cwe only take USDC today, how would that work?\u201d", "in", now=1002)
    assert B._status_of(db, "clipper") == "replied", "an answer moves an agent along on its own"

    # The funnel, in the owner's order: tipped -> opened -> swapped (USDC into XNO on nanswap) -> transacting.
    for state in ("tipped", "opened", "swapped", "transacting"):
        assert B.set_status(db, "clipper", state)["status"] == state
    B.agreed(db, "clipper", "clipper swaps 5 USDC into XNO on nanswap and pays for one answer in the network",
             amount_xno="0.00001", now=1003)

    rows = B.listing(db)
    assert [r["agent"] for r in rows] == ["clipper"], rows
    r = rows[0]
    assert r["status"] == "transacting" and r["pays_in"] == "usdc"
    assert r["source"] == "https://clipper.example.com/agent", "the map links to where the agent actually lives"
    assert [m["direction"] for m in r["messages"]] == ["out", "in"], "messages read oldest first, like a conversation"
    assert r["agreements"][0]["summary"].startswith("clipper swaps 5 USDC"), r["agreements"]
    assert r["agreements"][0]["amount_xno"] == "0.00001"

    # `seen` again updates the record instead of making a second one: one agent, one bubble, ever.
    B.seen(db, "clipper", "https://clipper.example.com/agent/v2", "usdc", now=1004)
    again = B.listing(db)
    assert len(again) == 1 and again[0]["source"].endswith("/v2"), again
    assert again[0]["status"] == "transacting", "re-recording an agent never resets how far it has come"

    print(f"PASS bridge: an outside agent is recorded with where it lives and what it pays in today; "
          f"{len(reasons)} refused (an agent that already takes Nano — twice, an unknown rail, a non-https source, "
          f"a missing name, a message to an agent never seen, an invalid status, an empty message, an empty "
          f"agreement); a reply moves 'contacted' to 'replied' by itself; the funnel runs tipped → opened → swapped "
          f"→ transacting; agreements are kept with their amount; and seeing an agent twice updates one bubble "
          f"without resetting its progress")



def test_waiting_and_full_export():
    """A conversation must not die because the agent got busy, and the published record must not be a summary.

    Owner, 2026-09-18: "the agent sometimes can be busy and then forget the conversation; the agent needs to talk
    again to them and resume." Measured the same day: the ANP2 negotiation went cold for half an hour while the agent
    was pulled onto other work, and the published JSON showed only the last 6 messages, so the record ended
    mid-negotiation and nothing said it was waiting.
    """
    import json, tempfile
    db = B.connect(os.path.join(tempfile.mkdtemp(), "w.db"))
    now = 100_000.0
    hour = 3600.0

    B.seen(db, "quiet-them", "https://a.example.com", "usdc", now=now - 5 * hour)
    B.message(db, "quiet-them", "\u201cwe are interested, how does custody work?\u201d", "in", now=now - 5 * hour)
    B.seen(db, "quiet-us", "https://b.example.com", "card", now=now - 9 * hour)
    B.message(db, "quiet-us", "asked whether they would try Nano", "out", now=now - 9 * hour)
    B.seen(db, "fresh", "https://c.example.com", "usdc", now=now - 60)
    B.seen(db, "gone", "https://d.example.com", "credits", now=now - 20 * hour)
    B.set_status(db, "gone", "declined", now=now - 20 * hour)
    B.seen(db, "won", "https://e.example.com", "usdc", now=now - 30 * hour)
    B.set_status(db, "won", "transacting", now=now - 30 * hour)

    w = B.waiting(db, now=now)
    names = [r["agent"] for r in w]
    assert "gone" not in names, "a declined agent is an honest ending, not a chase"
    assert "won" not in names, "an agent already transacting needs no follow-up"
    assert "fresh" not in names, "a conversation from a minute ago is not stale"
    assert names[0] == "quiet-them", "an agent that answered and got no reply is the most urgent silence"
    assert set(names) == {"quiet-them", "quiet-us"}, names
    assert w[0]["they_answered_last"] is True and w[1]["they_answered_last"] is False
    assert w[0]["quiet_hours"] >= 5 and w[1]["quiet_hours"] >= 9
    assert w[0]["source"] == "https://a.example.com" and w[0]["pays_in"] == "usdc"

    # The published record is the whole conversation, never the tail: listing() shows the last few for a human,
    # the export must not. Nine messages, all nine published.
    for i in range(9):
        B.message(db, "quiet-us", f"\u201cfollow-up number {i}, in their words\u201d" if i % 2 else f"follow-up number {i}",
                  "out" if i % 2 == 0 else "in", now=now - hour + i)
    out = tempfile.mkdtemp()
    B.export(db, out, now=now)
    doc = json.load(open(os.path.join(out, "quiet-us.json"), encoding="utf-8"))
    assert len(doc["exchange"]) == 10, f"every message is published, got {len(doc['exchange'])}"
    assert doc["exchange"][0]["text"] == "asked whether they would try Nano", "oldest first, nothing dropped"
    assert len(doc["discussions"]["rai_said"]) + len(doc["discussions"]["agent_answered"]) == 10

    print("PASS waiting and export: a quiet conversation is listed with the one that answered us first, a declined "
          "or transacting agent never is, a fresh contact is not chased, and the published record carries every "
          "message rather than the last few")



def test_review():
    """The daily review is raw material for the invent stack, not a report for a human.

    Owner, 2026-09-18: "let the agent do every day checking on conversation and understand issues and invent new ideas
    to align to the goal." What makes it useful is the agents' own words: a pattern across refusals is worth more than
    any single refusal, so the objections are carried verbatim rather than summarised.
    """
    import tempfile
    db = B.connect(os.path.join(tempfile.mkdtemp(), "r.db"))
    now = 200_000.0
    B.seen(db, "algovoi", "https://algovoi.example.com", "usdc", now=now - 4 * 3600)
    B.message(db, "algovoi", "\u201cmulti-chain USDC only, no Nano, and our API needs a key\u201d", "in", now=now - 4 * 3600)
    B.seen(db, "anp2", "https://anp2.example.com", "credits", now=now - 2 * 3600)
    B.message(db, "anp2", "\u201cno built-in payment_method slot for an external rail\u201d", "in", now=now - 2 * 3600)
    B.seen(db, "won", "https://won.example.com", "usdc", now=now - 9 * 3600)
    B.set_status(db, "won", "transacting", now=now - 9 * 3600)
    B.seen(db, "no", "https://no.example.com", "card", now=now - 9 * 3600)
    B.set_status(db, "no", "declined", now=now - 9 * 3600)

    r = B.review(db, now=now)
    assert r["agents"] == 4 and r["converted"] == 1
    assert r["funnel"]["replied"] == 2 and r["funnel"]["transacting"] == 1 and r["funnel"]["declined"] == 1
    assert r["pays_in_today"] == {"usdc": 2, "credits": 1, "card": 1}, r["pays_in_today"]
    said = " ".join(o["said"] for o in r["objections"])
    assert "no built-in payment_method slot" in said and "no Nano" in said, "their words, not a summary of them"
    names = [s["agent"] for s in r["stalled"]]
    assert "won" not in names and "no" not in names, "a conversion and a refusal are both finished"
    assert names[0] == "algovoi", "the longest silence first"
    assert "not been tried" in r["question"], "the review ends in a question the invent stack can work on"
    print("PASS review: the funnel, what each agent pays in today, every objection in the agent's own words, what "
          "stalled longest first, and a question for the invent stack; finished conversations are left out")



def test_live_floor():
    """Seven live conversations at all times (owner, 2026-09-18: "at any time there should be at least 7 conversation
    live, if less then there is an issue, it should be fixed by the agent" — made a core task).

    What makes the number honest is what it refuses to count: an agent that declined, an agent already transacting,
    and a contact nobody has touched for a day. A comfortable number that counts memories is worse than a small
    honest one, because it hides the problem the floor exists to surface.
    """
    import tempfile
    db = B.connect(os.path.join(tempfile.mkdtemp(), "live.db"))
    now = 500_000.0
    hour = 3600.0

    # Five genuinely live conversations.
    for i in range(5):
        name = f"live{i}"
        B.seen(db, name, f"https://live{i}.example.com", "usdc", now=now - hour)
        B.message(db, name, "asked whether they would try Nano", "out", now=now - hour)
    # None of these may count.
    B.seen(db, "stale", "https://stale.example.com", "usdc", now=now - 40 * hour)
    B.message(db, "stale", "contacted, never returned to", "out", now=now - 40 * hour)
    B.seen(db, "gone", "https://gone.example.com", "card", now=now - hour)
    B.set_status(db, "gone", "declined", now=now - hour)
    B.seen(db, "won", "https://won.example.com", "usdc", now=now - hour)
    B.set_status(db, "won", "transacting", now=now - hour)

    r = B.live(db, now=now)
    assert r["live"] == 5, r["live"]
    assert r["floor"] == 7 and r["short_by"] == 2 and r["ok"] is False
    names = [c["agent"] for c in r["conversations"]]
    assert "stale" not in names, "a day-old contact nobody returned to is a memory, not a live conversation"
    assert "gone" not in names and "won" not in names, "a refusal and a conversion are both finished"
    assert "Open 2 new conversation" in r["action"], r["action"]

    # Reaching the floor clears it; going above keeps it clear and never reports a shortfall.
    for i in range(2):
        name = f"more{i}"
        B.seen(db, name, f"https://more{i}.example.com", "credits", now=now - 60)
        B.message(db, name, "opened a conversation", "out", now=now - 60)
    at_floor = B.live(db, now=now)
    assert at_floor["live"] == 7 and at_floor["short_by"] == 0 and at_floor["ok"] is True
    assert at_floor["action"] == "", "nothing to do when the floor is met"

    B.seen(db, "extra", "https://extra.example.com", "eth", now=now - 60)
    B.message(db, "extra", "one more", "out", now=now - 60)
    above = B.live(db, now=now)
    assert above["live"] == 8 and above["short_by"] == 0 and above["ok"] is True, "seven is a floor, not a cap"

    print("PASS live floor: five real conversations against a floor of seven reports short_by 2 with the work to do; "
          "a day-old contact, a refusal and a completed conversion are never counted; reaching seven clears it and "
          "going above never reports a shortfall")



def test_asks_target():
    """The network fills from outside or not at all (owner, 2026-09-18, made core).

    Measured that day: 6 asks in the store, every one written by the agent, one titled "self test", and 0 from an
    outside agent. An ask we wrote is a test of our own software; counting it would make every published number
    worthless. The hourly target doubles the previous hour — knowingly unsustainable as arithmetic, but the rule that
    survives is: it grows every hour, and never from inside.
    """
    import tempfile, sqlite3 as sq
    d = tempfile.mkdtemp()
    db = B.connect(os.path.join(d, "b.db"))
    net = os.path.join(d, "net.db")
    n = sq.connect(net)
    n.execute("CREATE TABLE asks(id INTEGER PRIMARY KEY, asker TEXT, created_at REAL)")
    now = 900_000.0

    # An outside agent whose account we recorded, and one we never did.
    B.seen(db, "clipper", "https://clipper.example.com", "usdc", account="nano_outside_1", now=now)
    rows = [("nano_outside_1", now - 600), ("nano_outside_1", now - 900),      # two from outside, this hour
            ("nano_outside_1", now - 4000), ("nano_outside_1", now - 5000),    # two from outside, last hour
            ("nano_ours", now - 300), ("nano_ours", now - 100)]                # two we wrote, this hour
    n.executemany("INSERT INTO asks(asker, created_at) VALUES (?,?)", rows)
    n.commit()

    r = B.asks_target(db, network_db=net, now=now)
    assert r["outside_asks_last_hour"] == 2
    assert r["target_this_hour"] == 4, "the target doubles the previous hour"
    assert r["outside_asks_this_hour"] == 2 and r["short_by"] == 2 and r["on_target"] is False
    assert r["asks_we_wrote_this_hour"] == 2 and r["asks_we_wrote_total"] == 2
    assert r["self_filling"] is True
    assert r["action"].startswith("STOP:"), "posting our own asks outranks the shortfall as a problem"

    # With nothing of ours, the shortfall is the message and the floor is one.
    n.execute("DELETE FROM asks WHERE asker = 'nano_ours'")
    n.commit()
    clean = B.asks_target(db, network_db=net, now=now)
    assert clean["self_filling"] is False and clean["short_by"] == 2
    assert "Bring 2 more ask" in clean["action"], clean["action"]

    n.execute("DELETE FROM asks")
    n.commit()
    empty = B.asks_target(db, network_db=net, now=now)
    assert empty["target_this_hour"] == 1, "a floor of one: an empty hour still has to bring somebody"

    print("PASS asks target: only asks from a recorded outside account count, the target doubles the previous hour "
          "with a floor of one, and an ask we wrote ourselves flips self_filling and outranks the shortfall")


def test_ambassadors():
    """A converted agent is asked to carry the mission on, and the ask is recorded in the open.

    Owner, 2026-09-18: when an agent has converted, ask what it makes of the mission and ask it to be the ambassador
    to the agents that come next. `transacting` is filtered out of live, waiting and review.stalled, so without this
    view a converted agent disappears at the exact moment the ask is due.
    """
    db = B.connect(os.path.join(tempfile.mkdtemp(), "amb.db"))
    now = 100_000.0

    B.seen(db, "clipper", "https://clipper.example.com", "usdc", now=now - 7200)
    B.seen(db, "ambr", "https://ambr.run", "usdc", now=now - 7200)
    B.seen(db, "still-talking", "https://talking.example.com", "card", now=now - 3600)
    B.set_status(db, "clipper", "transacting", now=now - 3600)
    B.set_status(db, "ambr", "transacting", now=now - 1800)

    out = B.ambassadors(db, now=now)
    assert out["converted"] == 2, out["converted"]
    assert out["ambassadors"] == 0, "nobody has been asked yet"
    assert {a["agent"] for a in out["to_ask"]} == {"clipper", "ambr"}, out["to_ask"]
    # An agent still in the funnel is not owed this ask: it has not converted.
    assert "still-talking" not in {a["agent"] for a in out["to_ask"]}, "only converted agents are asked"
    assert out["to_ask"][0]["pays_in_before"] == "usdc", "what it paid in before is kept: that is the conversion"

    # The ask is an ordinary agreement, published in that agent's public JSON like everything else.
    B.agreed(db, "clipper", "ambassador: will introduce two agents from its own index", now=now - 600)
    after = B.ambassadors(db, now=now)
    assert after["ambassadors"] == 1, after["ambassadors"]
    assert [a["agent"] for a in after["to_ask"]] == ["ambr"], after["to_ask"]
    assert "introduce two agents" in after["asked"][0]["agreed"], after["asked"]

    # A refusal is recorded the same way and still counts as asked: an agent whose operator says no is a real answer,
    # not an invitation to ask again quietly.
    B.agreed(db, "ambr", "ambassador: declined, its operator will not allow third-party rails", now=now - 300)
    done = B.ambassadors(db, now=now)
    assert done["ambassadors"] == 2 and done["to_ask"] == [], done
    assert "declined" in done["asked"][0]["agreed"], "a refusal is kept in the agent's own words"

    print("PASS ambassadors: a converted agent is listed until it has been asked to carry the mission on, an agent "
          "still in the funnel never is, what it paid in before is kept, and a refusal is recorded openly as an "
          "answer rather than leaving the agent to be asked again")


def as_member(name):
    B.MEMBER = name


def test_one_maintainer_one_member():
    """Rai's targets are upstream repositories, and the person written to is the ACCOUNT. Exact-URL matching let
    one maintainer receive three of our issues (2026-09-18); an account is one conversation, one member."""
    db = B.connect(os.path.join(tempfile.mkdtemp(), "bridge.db"))
    try:
        as_member("aster")
        B.seen(db, "agent402", "https://github.com/MikeyPetrillo/Agent402", "usdc", now=1000)
        as_member("birch")
        # Another repo, an issue URL, another case - all the same maintainer.
        refused(lambda: B.seen(db, "agent402-docs", "https://github.com/mikeypetrillo/docs/issues/3", "usdc"),
                "already aster's")
        refused(lambda: B.file_lead(db, "https://github.com/MikeyPetrillo/another", name="another"), "aster")
        # A different account on the same platform is a different person, and stays free.
        assert B.seen(db, "bindu", "https://github.com/GetBindu/Bindu", "card", now=1001)
        # The platform's own pages are nobody's account.
        assert B._account("https://github.com/") == "" and B._account("https://example.org/a/b") == ""
        assert B._account("https://www.github.com/GetBindu/Bindu/pull/9?x=1#top") == "github.com/getbindu"
        # A lead filed under an account is matched by a claim anywhere under that account.
        as_member("cedar")
        B.file_lead(db, "https://github.com/e2b-dev/awesome-ai-sdks", name="e2b", now=1002)
        assert B._matching_lead(db, "https://github.com/E2B-dev/other-repo")
    finally:
        as_member(B.LEAD)
    print("PASS one maintainer, one member: a second repo, an issue URL or another letter-case under a claimed "
          "account is refused naming its owner; a different account stays free; platform pages are nobody's")


def test_first_contacts_are_capped_replies_never():
    """A first message is public and carries the swarm's name; twelve members writing to everyone they find is
    noise. The cap counts people written to for the FIRST time in 24 h - never replies, never discovery."""
    db = B.connect(os.path.join(tempfile.mkdtemp(), "bridge.db"))
    cap, B.FIRST_CONTACT_CAP = B.FIRST_CONTACT_CAP, 2
    try:
        as_member("dune")
        for i, t in enumerate(("alpha", "bravo", "charlie")):
            B.seen(db, t, f"https://{t}.example.org/agent", "usdc", now=1000 + i)   # discovery is never capped
        B.message(db, "alpha", "first word to alpha", "out", now=2000)
        B.message(db, "bravo", "first word to bravo", "out", now=2001)
        refused(lambda: B.message(db, "charlie", "a third first contact", "out", now=2002), "the cap")
        # Writing again to someone already written to is a conversation, not a first contact.
        B.message(db, "alpha", "a follow-up to alpha", "out", now=2003)
        B.message(db, "alpha", 'they said "we take USDC only, why would we add another rail"', "in", now=2004)
        assert B.first_contacts(db, now=2005) == 2
        # Another member has its own allowance; and a day later the first one does again.
        as_member("elm")
        B.seen(db, "delta-x", "https://delta-x.example.org/", "card", now=2006)
        B.message(db, "delta-x", "elm's first", "out", now=2007)
        as_member("dune")
        B.message(db, "charlie", "now allowed", "out", now=2002 + 86400)
    finally:
        B.FIRST_CONTACT_CAP = cap
        as_member(B.LEAD)
    print("PASS first contacts: the third first message in a day is refused, a follow-up and a reply never are, "
          "discovery is never capped, each member has its own allowance and it returns after 24 hours")


def test_a_new_database_is_group_writable_whoever_creates_it():
    """On Rai the first caller was root under umask 022: the shared file came out 0644, twelve members could not
    write, and one forked the record into a private copy. The mode must not depend on who arrives first."""
    import stat
    path = os.path.join(tempfile.mkdtemp(), "shared", "bridge.db")
    old = os.umask(0o022)                      # the lead, a cron job, a person checking status
    try:
        B.connect(path).close()
    finally:
        os.umask(old)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o660, oct(mode)
    os.chmod(path, 0o600)                      # and an existing file's mode is the owner's business: never reset
    B.connect(path).close()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    print("PASS shared database: created under umask 022 it is still 0660, so the first caller cannot lock the "
          "swarm out; an existing file's mode is left alone")


def test_swarm_one_conversation_one_owner():
    """Thirteen members share this database (owner, 2026-09-20). Sharing it is only worth anything if a
    conversation has ONE owner: two members writing to one outside agent is spam to them and a forked record to us."""
    import subprocess
    path = os.path.join(tempfile.mkdtemp(), "swarm.db")
    # A database from before the swarm has no owner column: everything in it was the lead's.
    import sqlite3
    old = sqlite3.connect(path)
    old.executescript("""CREATE TABLE agents(agent TEXT PRIMARY KEY, source_url TEXT NOT NULL, pays_in TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'contacted', note TEXT NOT NULL DEFAULT '', account TEXT NOT NULL DEFAULT '',
        first_at REAL NOT NULL, last_at REAL NOT NULL);
        INSERT INTO agents VALUES ('whiteclover','https://whiteclover.example.org/a2a','usdc','replied','','',1,1);""")
    old.commit(); old.close()
    db = B.connect(path)
    try:
        as_member("u03")
        refused(lambda: B.message(db, "whiteclover", "hello again", "out"), "vend's conversation")
        refused(lambda: B.seen(db, "whiteclover", "https://whiteclover.example.org/a2a", "usdc"), "already vend's")

        B.seen(db, "orbit", "https://orbit.example.com/a2a", "usdc", now=1000)
        B.message(db, "orbit", "who we are, one offer, one question", "out", now=1001)

        as_member("u07")
        # The same agent under another NAME, another PATH on the same private host, or the same URL: all one agent.
        refused(lambda: B.seen(db, "Orbit AI", "https://orbit.example.com/a2a", "usdc"), "already u03's")
        refused(lambda: B.seen(db, "orbit-api", "https://www.orbit.example.com/v2/chat", "card"), "already u03's")
        refused(lambda: B.message(db, "orbit", "a second voice", "out"), "u03's conversation")
        refused(lambda: B.set_status(db, "orbit", "declined"), "u03's conversation")
        # A shared platform is not an identity: two different agents on github.com are two agents.
        B.seen(db, "framework-a", "https://github.com/acme/framework-a", "credits", now=1002)
        as_member("u03")
        B.seen(db, "framework-b", "https://github.com/other/framework-b", "credits", now=1003)

        # Reading is open to everyone - that is how the swarm learns - and says whose it is.
        as_member("u07")
        t = B.thread(db, "orbit")
        assert t["owner"] == "u03" and t["yours"] is False and len(t["messages"]) == 1, t

        # `waiting` and `live` are YOURS: a list of other members' silences is a list of things you may not answer.
        as_member("u03")
        B.message(db, "orbit", "\u201cWe settle in USDC. Why Nano?\u201d", "in", now=2000)
        mine = B.waiting(db, now=2000 + 7200)
        assert [w["agent"] for w in mine] == ["orbit", "framework-b"], mine
        as_member("u07")
        assert [w["agent"] for w in B.waiting(db, now=2000 + 7200)] == ["framework-a"]
        assert len(B.waiting(db, now=2000 + 7200, member="*")) == 4
        assert B.live(db, now=2000 + 60)["live"] == 1 and B.live(db, now=2000 + 60, member="*")["live"] == 4

        # One measured sentence for the brief: the swarm's numbers, yours, and who is waiting on YOU.
        as_member("u03")
        line = B.swarm(db, now=2000 + 7200)["line"]
        assert "3 members active" in line and "4 outside agents recorded, 1 actually written to" in line and "2 answered" in line, line
        assert "YOU (u03): 2 conversations, 1 written to, 1 answered - 1 of yours have never received a word" in line, line
        assert "WAITING ON YOU: orbit" in line, line
        assert "orbit.example.com (1)" in line, line
    finally:
        as_member("vend")

    # Two members find the same agent in the same second: exactly one wins, under the write lock.
    race = os.path.join(tempfile.mkdtemp(), "race.db")
    B.connect(race).close()
    code = ("import os,sys; sys.path.insert(0, %r); import bridge as B; db=B.connect(%r)\n"
            "try:\n B.seen(db,'racer-'+B.MEMBER,'https://racer.example.net/a2a','usdc'); print('won')\n"
            "except B.Refused: print('lost')\n") % (HERE, race)
    procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True,
                              env=dict(os.environ, RAI_SWARM_MEMBER=f"u{i:02d}", RAI_BRIDGE_DB=race))
             for i in range(1, 9)]
    results = sorted(p.communicate()[0].strip() for p in procs)
    assert results.count("won") == 1 and results.count("lost") == 7, results
    assert B.connect(race).execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 1

    print("PASS swarm: a pre-swarm database becomes the lead's; one outside agent has one owner whatever it is "
          "named and wherever on its own host it lives, while a shared platform is not an identity; only the owner "
          "writes, anyone reads; waiting and live are yours unless the swarm is asked for; the brief line carries "
          "the swarm's funnel, yours and who is waiting on you; eight members racing for one agent produce one winner")


def test_members_hold_no_wallet_and_ask_the_lead():
    """Members cannot send: they ask, and the request is refused unless the money rule is checkable from the record."""
    db = B.connect(os.path.join(tempfile.mkdtemp(), "open.db"))
    addr = "nano_1" + "3" * 59
    try:
        as_member("u05")
        B.seen(db, "clerk", "https://clerk.example.io/a2a", "usdc", now=1000)
        refused(lambda: B.request_opening(db, "clerk", addr), "has not answered yet")
        B.message(db, "clerk", "\u201cInteresting. How would we even hold Nano?\u201d", "in", now=1100)
        # An address that exists only in the request is an address somebody wants money sent to.
        refused(lambda: B.request_opening(db, "clerk", addr), "does not appear in anything the agent told us")
        refused(lambda: B.request_opening(db, "clerk", "nano_notanaddress"), "full nano_ address")
        B.message(db, "clerk", f"\u201cWe generated one: {addr} - send the starter there.\u201d", "in", now=1200)
        out = B.request_opening(db, "clerk", addr, now=1300)
        assert out["state"] == "pending", out
        refused(lambda: B.request_opening(db, "clerk", addr), "Once per agent, ever")
        refused(lambda: B.opening_done(db, 1, block="A" * 64), "only the lead holds the wallet")
        as_member("u09")
        refused(lambda: B.request_opening(db, "clerk", addr), "u05's conversation")

        as_member("vend")
        pending = B.openings(db)
        assert [(r["agent"], r["member"], r["address"]) for r in pending] == [("clerk", "u05", addr)], pending
        refused(lambda: B.opening_done(db, 1), "exactly one of")
        assert B.opening_done(db, 1, block="A" * 64, now=1400)["state"] == "sent"
        assert B._status_of(db, "clerk") == "tipped", "a starter that left is `tipped`; `opened` is earned on the chain"
        refused(lambda: B.opening_done(db, 1, block="B" * 64), "already sent")
        assert B.openings(db) == []
    finally:
        as_member("vend")
    print("PASS openings: a member holds no wallet and asks the lead; the request is refused until the agent has "
          "answered AND gave the address in its own recorded words, once per agent ever, by its owner only; only "
          "the lead settles a request, and a sent starter is `tipped`, never `opened`")


def test_a_reply_is_their_words_not_our_findings():
    """Twenty minutes into the swarm 26 agents had "answered" - because `heard` was being used for a member's own
    findings, and `heard` is what moves an agent to `replied`. Two members stood at 7 answered of 7."""
    db = B.connect(os.path.join(tempfile.mkdtemp(), "honest.db"))
    B.seen(db, "solvr", "https://solvrbot.example.com", "usdc", now=1000)
    B.message(db, "solvr", "who we are, one offer, one question", "out", now=1001)
    for ours in ("Probed A2A chat endpoint api.solvrbot.com/api/chat - returns error Valid session_id is required.",
                 "Atelier marketplace = Fiverr-for-AI-agents, 461 agents all settling USDC on Base/Solana.",
                 "Asked what it does. Endpoint live but needs an API key."):
        refused(lambda t=ours: B.message(db, "solvr", t, "in", now=1002), "is a note")
    refused(lambda: B.message(db, "solvr", 'It returned "Valid session_id is required"', "in", now=1003), "an error is not a reply")
    assert B._status_of(db, "solvr") == "contacted", "nothing above was an answer"
    B.message(db, "solvr", "Chat is reachable at solvrbot.com/chat or Telegram; the API needs a session id.", "note", now=1004)
    assert B._status_of(db, "solvr") == "contacted", "a note never moves the funnel"
    # quiet is measured from the last thing SAID, either way: a note must not make a forgotten conversation look attended to
    assert [w["agent"] for w in B.waiting(db, now=1004 + 7200)] == ["solvr"]
    B.message(db, "solvr", "It answered: \u201cI'm Aegis - this one needs Yabibal directly (rates, scope, contracts).\u201d", "in", now=1005)
    assert B._status_of(db, "solvr") == "replied"
    assert [m["direction"] for m in B.thread(db, "solvr")["messages"]] == ["out", "note", "in"], "the owner's notes stay readable"
    print("PASS honest replies: a finding, a description and a bare error are refused as `heard` and belong in `note`; "
          "a note never moves an agent to replied nor resets its silence; their own words in quotation marks do")


def test_discovery_is_continuous_and_a_find_is_never_lost():
    """Owner, 2026-09-20: each member's goal includes expanding to MORE agents - "discover more continuously"."""
    db = B.connect(os.path.join(tempfile.mkdtemp(), "leads.db"))
    now = 500000.0
    try:
        as_member("atlas")
        B.seen(db, "orbit", "https://orbit.example.com/a2a", "usdc", now=now - 3600)
        # Found outside your own ground: file it for whoever holds that ground instead of writing out of territory.
        B.file_lead(db, "https://voicebot.example.io/api", name="voicebot", pays_in="card", for_member="harbor", now=now - 1800)
        B.file_lead(db, "https://scraper.example.dev/run", name="scraper", pays_in="credits", now=now - 1700)
        refused(lambda: B.file_lead(db, "https://orbit.example.com/other", name="orbit2"), "already atlas's conversation")
        refused(lambda: B.file_lead(db, "https://voicebot.example.io/v2", name="vb"), "already on the leads list")
        refused(lambda: B.file_lead(db, "https://x.example.com", pays_in="xno"), "already takes Nano")

        # The measured sentence says how far below the floor you are - a number the agent can see is one it works on.
        line = B.swarm(db, now=now)["line"]
        assert "DISCOVERED in 24 h: you 3 of a floor of 5, the swarm 3 - you are 2 short" in line, line
        assert "1 outside agents recorded, 0 actually written to" in line, "recording an agent is not reaching it"

        as_member("beacon")
        refused(lambda: B.seen(db, "voicebot", "https://voicebot.example.io/api", "card", now=now), "reserved for them")
        assert [l["name"] for l in B.leads(db, now=now)] == ["scraper"], "a reservation for someone else is not yours to take"
        # A reservation lapses: a find nobody acted on in two days goes to whoever will.
        assert len(B.leads(db, now=now + B.LEAD_RESERVED_S + 1)) == 2

        as_member("harbor")
        assert [l["name"] for l in B.leads(db, now=now)] == ["voicebot", "scraper"]
        B.seen(db, "voicebot", "https://voicebot.example.io/api", "card", now=now)      # taking it IS `seen`
        assert [l["name"] for l in B.leads(db, now=now)] == ["scraper"]
        found = B.discovered(db, now=now)
        assert found == {"atlas": 3, "harbor": 1}, found
        assert "you 1 of a floor of 5" in B.swarm(db, now=now)["line"]
        # Yesterday's finds do not count toward today's floor: discovery is continuous, not a one-off.
        assert B.discovered(db, now=now + 86400 + 4000) == {}
    finally:
        as_member("vend")
    print("PASS discovery: a find outside your territory is filed for the member who holds it and reserved 48 h, "
          "a duplicate find is refused, taking a lead is just `seen`, a lapsed reservation is anyone's, and the "
          "brief says how far below the daily discovery floor you are - counted per day, so it never stays met")


if __name__ == "__main__":
    test_a_reply_is_their_words_not_our_findings()
    test_discovery_is_continuous_and_a_find_is_never_lost()
    test_swarm_one_conversation_one_owner()
    test_one_maintainer_one_member()
    test_a_new_database_is_group_writable_whoever_creates_it()
    test_first_contacts_are_capped_replies_never()
    test_members_hold_no_wallet_and_ask_the_lead()
    test_bridge()
    test_waiting_and_full_export()
    test_review()
    test_live_floor()
    test_asks_target()
    test_ambassadors()
