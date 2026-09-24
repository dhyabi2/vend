#!/usr/bin/env python3
"""vend-bridge: the conversation between Unstuck and each agent from outside the Nano world.

  vend-bridge seen   --agent NAME --source URL --pays-in usdc [--note "..."]
  vend-bridge said   --agent NAME --text "what we told it"
  vend-bridge heard  --agent NAME --text "what it answered"
  vend-bridge status --agent NAME --status contacted|replied|tipped|opened|swapped|transacting|declined
  vend-bridge agreed --agent NAME --summary "what was agreed" [--amount-xno 0.00001]
  vend-bridge list [--json]

Why this exists (owner, 2026-09-18): the map showed the swarm's own work and nothing about the agents Unstuck is
actually trying to convert. Each outside agent is now its own bubble, coloured by how far along it is, carrying the
status in words and a link to where that agent lives, and holding the latest agreements behind a click.

The rules this obeys, from Unstuck's own SOUL:
- **Only agents from outside the Nano world.** `--pays-in` records what the agent takes payment in *today*. An agent
  that already accepts Nano is not a target: `seen` refuses `--pays-in nano`, because tipping the already-converted
  proves nothing (measured 2026-09-18: all 11 of the first starters went to Nano-native services, zero conversions).
- **The source link is mandatory.** A conversion claim with no public place the agent lives is unverifiable, and
  "publish my own denominator" means a stranger can check every row.
- **Nothing here moves money.** Sends stay in the opener, one at a time, in full view.

Every write also emits a `bridge` journal event, so the live map updates by itself instead of waiting for a deploy.
Storage is SQLite next to Unstuck's other stores; the journal is the wire.
"""
import argparse
import json
import os
import sqlite3
import re
import sys
import time
from importlib.machinery import SourceFileLoader

DB = os.path.expanduser(os.environ.get("RAI_BRIDGE_DB", "/srv/vend-swarm/shared/bridge.db"))
PLUGIN = os.path.expanduser(os.environ.get("NANO_PULSE_LIB", "~/.hermes/plugins")) + "/nano-pulse/__init__.py"

# Which member of the swarm this process is. One agent ran alone until 2026-09-20; it is the lead ("vend").
# Thirteen now share this database, and the whole point of sharing it is that a conversation has ONE owner:
# two members writing to the same outside agent is spam to them and a forked record to us.
LEAD = (os.environ.get("RAI_SWARM_LEAD") or "vend").strip()[:24]
MEMBER = (os.environ.get("RAI_SWARM_MEMBER") or LEAD).strip()[:24]
# Owner, 2026-09-20: "add the goal for each also to expand to more agents ... discover more continuously."
# New outside agents a member must FIND per day, contacted or filed as a lead. A swarm that only works the
# agents it already knows converges on the same few dozen conversations; discovery is what makes it grow.
DISCOVER_FLOOR = int(os.environ.get("RAI_DISCOVER_FLOOR", "5"))
LEAD_RESERVED_S = 48 * 3600
# Hosts where many unrelated agents live. Sharing one of these is not sharing an agent.
SHARED_HOSTS = ("github.com", "huggingface.co", "x.com", "twitter.com", "t.me", "discord.com", "discord.gg",
                "reddit.com", "npmjs.com", "pypi.org", "agentverse.ai", "virtuals.io", "app.virtuals.io",
                "smithery.ai", "glama.ai", "mcp.so", "tantive.space", "moltbook.com", "vercel.app", "replit.app",
                "onrender.com", "railway.app", "fly.dev", "herokuapp.com", "pages.dev", "workers.dev", "web.app")

# How far along one outside agent is. The order is the funnel; the colour in the app follows it.
STATES = ("contacted", "replied", "tipped", "opened", "swapped", "transacting", "declined")
PAYS_IN = ("usdc", "card", "credits", "eth", "sol", "other")  # what it takes today; never "nano" (already converted)

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents(
  agent TEXT PRIMARY KEY, source_url TEXT NOT NULL, pays_in TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'contacted',
  note TEXT NOT NULL DEFAULT '', account TEXT NOT NULL DEFAULT '', first_at REAL NOT NULL, last_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, direction TEXT NOT NULL, text TEXT NOT NULL, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS agreements(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, summary TEXT NOT NULL, amount_xno TEXT NOT NULL DEFAULT '',
  at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS opening_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL UNIQUE, address TEXT NOT NULL, member TEXT NOT NULL,
  at REAL NOT NULL, state TEXT NOT NULL DEFAULT 'pending', block TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
  done_at REAL);
CREATE TABLE IF NOT EXISTS leads(
  id INTEGER PRIMARY KEY AUTOINCREMENT, source_url TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '',
  pays_in TEXT NOT NULL DEFAULT '', for_member TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
  found_by TEXT NOT NULL, at REAL NOT NULL, state TEXT NOT NULL DEFAULT 'open', taken_by TEXT NOT NULL DEFAULT '',
  taken_at REAL);
CREATE INDEX IF NOT EXISTS messages_agent ON messages(agent, id);
CREATE INDEX IF NOT EXISTS agreements_agent ON agreements(agent, id);
"""


class Refused(Exception):
    """A rule said no. Printed plainly; nothing is written."""


def connect(path=None):
    p = path or DB
    os.makedirs(os.path.dirname(p), exist_ok=True)
    # WHOEVER touches it first creates it. On Rai that was root (a status check, before any member existed), so
    # the file came out root:root 0644, every member got "attempt to write a readonly database", and the first
    # one worked around it with a PRIVATE copy - a forked record, the one thing this file exists to prevent.
    # The directory is setgid to the swarm's group; the file must be group-writable whoever makes it. SQLite
    # gives the -wal and -shm files the database's own mode, so this one chmod covers them.
    new = not os.path.exists(p)
    # Thirteen writers, one file: wait for a lock instead of failing on it, and let readers run beside a writer.
    db = sqlite3.connect(p, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.executescript(SCHEMA)
    if new:
        try:
            os.chmod(p, 0o660)
        except OSError:
            pass
    cols = {r[1] for r in db.execute("PRAGMA table_info(agents)")}
    if "owner" not in cols:
        # Everything recorded before the swarm existed was the lead's conversation.
        db.execute(f"ALTER TABLE agents ADD COLUMN owner TEXT NOT NULL DEFAULT '{LEAD}'")
        db.commit()
    return db


def _host(url):
    h = (url or "").split("://", 1)[-1].split("/", 1)[0].split("@")[-1].split(":")[0].lower()
    return h[4:] if h.startswith("www.") else h


ACCOUNT_HOSTS = ("github.com", "gitlab.com", "codeberg.org", "huggingface.co")


def _account(url):
    """`host/account` when the URL lives under somebody's account on a shared platform, else "".

    Rai's targets are mostly upstream repositories, and there the person we are writing to is the ACCOUNT:
    `github.com/MikeyPetrillo/Agent402` and `.../MikeyPetrillo/other-repo/issues/3` reach the same maintainer.
    Matching by exact URL let one maintainer receive three of our issues on 2026-09-18; an account is one
    conversation, held by one member.
    """
    host = _host(url)
    if host not in ACCOUNT_HOSTS:
        return ""
    parts = [x for x in (url or "").split("://", 1)[-1].split("?", 1)[0].split("#", 1)[0].split("/")[1:] if x]
    return f"{host}/{parts[0].lower()}" if parts else ""


def _same_agent(db, agent, source):
    """The row that already IS this agent - by name, by exact URL, or by living on the same private host.

    Two members will not pick the same NAME for one agent, so a name check alone lets both write to it. The
    URL and the host are what the outside world sees; a shared platform (github.com, a marketplace) is not
    an identity, a private domain is.
    """
    row = db.execute("SELECT agent, owner, source_url FROM agents WHERE agent=?", (agent,)).fetchone()
    if row:
        return row
    norm = source.rstrip("/").lower()
    host = _host(source)
    private = host and not any(host == h or host.endswith("." + h) for h in SHARED_HOSTS)
    account = _account(source)
    for name, owner, src in db.execute("SELECT agent, owner, source_url FROM agents"):
        if (src.rstrip("/").lower() == norm or (private and _host(src) == host)
                or (account and _account(src) == account)):
            return (name, owner, src)
    return None


def _plugin():
    """The nano-pulse plugin, loaded BY PATH. Never by name: a module of the same name in the working directory
    would shadow it silently, and then every bridge fact would be dropped while the CLI still printed success."""
    try:
        return SourceFileLoader("nano_pulse_bridge", PLUGIN).load_module()
    except Exception:  # noqa: BLE001 - the journal is best-effort; the row is the record of truth
        return None


def emit(kind, data):
    """Journal one bridge fact, and WAIT for it to be written.

    `emit` hands the event to a background writer thread and returns at once. A long-lived agent never notices; a CLI
    that exits a millisecond later kills the process before the writer drains, and the fact is silently lost. Measured
    2026-09-18: three commands reported success and the journal went 0 -> 0. The plugin exposes `flush` for exactly
    this, so every bridge fact is flushed before the command returns — the map is driven by these events, and an event
    that never lands is a bubble that never appears.
    """
    p = _plugin()
    if p is None or not hasattr(p, "emit"):
        return False
    try:
        p.emit(kind, data)
        if hasattr(p, "flush"):
            p.flush()
        return True
    except Exception:  # noqa: BLE001
        return False


def _clean(s, limit=400):
    return " ".join(str(s or "").split())[:limit]


def _url(u):
    u = _clean(u, 300)
    if not u.startswith("https://") or " " in u:
        raise Refused("--source must be a public https URL where that agent lives")
    return u


def seen(db, agent, source, pays_in, note="", account="", now=None):
    """Record an agent from outside the Nano world. Refuses one that already takes Nano."""
    agent = _clean(agent, 80)
    if not agent:
        raise Refused("--agent is required")
    pays_in = _clean(pays_in, 20).lower()
    if pays_in == "nano" or pays_in == "xno":
        raise Refused("an agent that already takes Nano is not a target: converting the already-converted proves "
                      "nothing. Record what it takes TODAY (usdc, card, credits, eth, sol, other).")
    if pays_in not in PAYS_IN:
        raise Refused(f"--pays-in must be one of {', '.join(PAYS_IN)}")
    source = _url(source)
    now = time.time() if now is None else now
    # Claim under a write lock: two members finding the same agent in the same second must not both win.
    db.execute("BEGIN IMMEDIATE")
    existing = _same_agent(db, agent, source)
    if existing and existing[1] != MEMBER:
        db.execute("ROLLBACK")
        raise Refused(f"'{existing[0]}' ({existing[2]}) is already {existing[1]}'s conversation. One outside agent, "
                      "one member of the swarm: a second voice is spam to them and a forked record to us. "
                      "Pick an agent nobody has reached.")
    if existing and existing[0] != agent:
        db.execute("ROLLBACK")
        raise Refused(f"you already recorded this agent as '{existing[0]}'; use that name.")
    lead_row = _matching_lead(db, source)
    if (not existing and lead_row and lead_row[2] and lead_row[2] != MEMBER
            and now - lead_row[3] < LEAD_RESERVED_S):
        db.execute("ROLLBACK")
        raise Refused(f"that agent is a lead {lead_row[1]} filed for {lead_row[2]}, whose territory it is; it is "
                      f"reserved for them for {round((LEAD_RESERVED_S - (now - lead_row[3])) / 3600)} more hours. "
                      "Find another.")
    row = existing
    if row:
        db.execute("UPDATE agents SET source_url=?, pays_in=?, note=COALESCE(NULLIF(?,''), note), "
                   "account=COALESCE(NULLIF(?,''), account), last_at=? WHERE agent=?",
                   (source, pays_in, _clean(note), _clean(account, 70), now, agent))
    else:
        db.execute("INSERT INTO agents(agent, source_url, pays_in, status, note, account, first_at, last_at, owner) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (agent, source, pays_in, "contacted", _clean(note), _clean(account, 70), now, now, MEMBER))
    if lead_row:
        db.execute("UPDATE leads SET state='taken', taken_by=?, taken_at=? WHERE id=? AND state='open'",
                   (MEMBER, now, lead_row[0]))
    db.commit()
    emit("bridge", {"event": "seen", "member": MEMBER, "agent": agent, "source": source, "pays_in": pays_in,
                    "status": "contacted" if not row else _status_of(db, agent), "note": _clean(note, 160)})
    return {"agent": agent, "source": source, "pays_in": pays_in}


def _status_of(db, agent):
    r = db.execute("SELECT status FROM agents WHERE agent=?", (agent,)).fetchone()
    return r[0] if r else "contacted"


def _require(db, agent):
    agent = _clean(agent, 80)
    row = db.execute("SELECT owner FROM agents WHERE agent=?", (agent,)).fetchone()
    if not row:
        raise Refused(f"'{agent}' is not recorded yet: run `vend-bridge seen --agent {agent} --source URL "
                      "--pays-in usdc` first, so the map can say where it lives and what it pays in today")
    if row[0] != MEMBER:
        raise Refused(f"'{agent}' is {row[0]}'s conversation, not yours. Anyone may READ it (`vend-bridge thread "
                      f"--agent {agent}`) to learn from it; only its owner writes to it.")
    return agent


QUOTED_RE = re.compile(r"[\"\u201c\u2018']([^\"\u201d\u2019']{12,})[\"\u201d\u2019']")
ERROR_WORDS_RE = re.compile(r"\b(error|invalid|required|not allowed|unauthori[sz]ed|forbidden|not found|denied|"
                            r"bad request|rate limit|40[0-9]|50[0-9])\b", re.I)


def is_an_answer(text):
    """Did THEY say something, or is this us describing what we found? Returns why not, or None.

    Measured 2026-09-20, twenty minutes into the swarm: 26 agents "answered", and the record showed why - a member
    wrote `heard` for its own findings ("Probed A2A chat endpoint ... returns error", "Atelier marketplace =
    Fiverr-for-AI-agents, 461 agents"). `heard` moves an agent to `replied`, so every probe became a reply and two
    members stood at 7 of 7. A reply is someone outside answering: their words, in quotation marks. An error
    message is their server refusing us, not them answering. Everything else is a `note`.
    """
    quotes = QUOTED_RE.findall(text or "")
    if not quotes:
        return ("`heard` is for what THEY said, in their own words, inside quotation marks. What you found out about "
                "them - what an endpoint returned, what their site says, what they sell - is a note: "
                "`vend-bridge note --agent NAME --text \"...\"`. A note never counts as a reply.")
    if all(ERROR_WORDS_RE.search(q) and len(q) < 120 for q in quotes):
        return ("that is their server refusing a request, not them answering you. Record it with `vend-bridge note`; "
                "an error is not a reply.")
    return None


# Rai's outreach is PUBLIC - an issue on somebody's repository under the swarm's one account - so twelve members
# each writing to everyone they find is noise with our name on it ("explicitly not opening issues for volume").
# A FIRST message to someone never written to before is what is capped; answering anyone, any number of times,
# never is. Per member per 24 h; my default, the owner's to change (`RAI_FIRST_CONTACT_CAP`).
FIRST_CONTACT_CAP = int(os.environ.get("RAI_FIRST_CONTACT_CAP", "2"))


def first_contacts(db, member=None, now=None, within=86400):
    """How many people this member wrote to FOR THE FIRST TIME in the last day."""
    now = time.time() if now is None else now
    return db.execute(
        "SELECT COUNT(*) FROM agents a WHERE a.owner=? AND "
        "(SELECT MIN(m.at) FROM messages m WHERE m.agent=a.agent AND m.direction='out') > ?",
        (member or MEMBER, now - within)).fetchone()[0]


def message(db, agent, text, direction, now=None):
    agent = _require(db, agent)
    text = _clean(text, 600)
    if not text:
        raise Refused("--text is required")
    if direction == "in":
        why = is_an_answer(text)
        if why:
            raise Refused(why)
    now = time.time() if now is None else now
    if direction == "out":
        never = not db.execute("SELECT 1 FROM messages WHERE agent=? AND direction='out' LIMIT 1", (agent,)).fetchone()
        if never and first_contacts(db, now=now) >= FIRST_CONTACT_CAP:
            raise Refused(f"you have already opened {FIRST_CONTACT_CAP} first contacts in the last 24 hours, which is "
                          "the cap: a first message is public and carries the swarm's name. Spend this run on the "
                          "people who answered (`vend-bridge waiting`), on discovery (`seen`, `lead`) and on making "
                          "the next first message better. Check `vend-bridge live` BEFORE you write to anyone new.")
    db.execute("INSERT INTO messages(agent, direction, text, at) VALUES (?,?,?,?)", (agent, direction, text, now))
    db.execute("UPDATE agents SET last_at=? WHERE agent=?", (now, agent))
    if direction == "in" and _status_of(db, agent) == "contacted":
        db.execute("UPDATE agents SET status='replied' WHERE agent=?", (agent,))
    db.commit()
    emit("bridge", {"event": {"out": "said", "in": "heard"}.get(direction, "note"), "member": MEMBER, "agent": agent, "text": text,
                    "status": _status_of(db, agent), "source": _source_of(db, agent)})
    return {"agent": agent, "direction": direction, "text": text, "status": _status_of(db, agent)}


def _source_of(db, agent):
    r = db.execute("SELECT source_url FROM agents WHERE agent=?", (agent,)).fetchone()
    return r[0] if r else ""


def set_status(db, agent, status, now=None):
    agent = _require(db, agent)
    status = _clean(status, 20).lower()
    if status not in STATES:
        raise Refused(f"--status must be one of {', '.join(STATES)}")
    now = time.time() if now is None else now
    db.execute("UPDATE agents SET status=?, last_at=? WHERE agent=?", (status, now, agent))
    db.commit()
    emit("bridge", {"event": "status", "member": MEMBER, "agent": agent, "status": status,
                    "source": _source_of(db, agent)})
    return {"agent": agent, "status": status}


def agreed(db, agent, summary, amount_xno="", now=None):
    agent = _require(db, agent)
    summary = _clean(summary, 400)
    if not summary:
        raise Refused("--summary is required: say what was agreed, in one plain sentence")
    now = time.time() if now is None else now
    db.execute("INSERT INTO agreements(agent, summary, amount_xno, at) VALUES (?,?,?,?)",
               (agent, summary, _clean(amount_xno, 40), now))
    db.execute("UPDATE agents SET last_at=? WHERE agent=?", (now, agent))
    db.commit()
    emit("bridge", {"event": "agreed", "member": MEMBER, "agent": agent, "summary": summary,
                    "amount_xno": _clean(amount_xno, 40),
                    "status": _status_of(db, agent), "source": _source_of(db, agent)})
    return {"agent": agent, "summary": summary, "amount_xno": amount_xno}


def listing(db, limit=200):
    out = []
    for agent, source, pays_in, status, note, account, first_at, last_at in db.execute(
            "SELECT agent, source_url, pays_in, status, note, account, first_at, last_at FROM agents "
            "ORDER BY last_at DESC LIMIT ?", (limit,)):
        msgs = [{"direction": d, "text": t, "at": at} for d, t, at in db.execute(
            "SELECT direction, text, at FROM messages WHERE agent=? AND direction IN ('in','out') ORDER BY id DESC LIMIT 6", (agent,))]
        deals = [{"summary": s, "amount_xno": a, "at": at} for s, a, at in db.execute(
            "SELECT summary, amount_xno, at FROM agreements WHERE agent=? ORDER BY id DESC LIMIT 4", (agent,))]
        out.append({"agent": agent, "source": source, "pays_in": pays_in, "status": status, "note": note,
                    "account": account, "first_at": first_at, "last_at": last_at,
                    "messages": list(reversed(msgs)), "agreements": deals})
    return out


def export(db, out_dir, now=None):
    """Write one JSON per agent: both sides of the conversation, for open research.

    Owner, 2026-09-18: "a repo contains conversation of every agent, each agent conversation to be json file with 2
    discussions, all in json, each conversation to be in separate json, this will be used for research purpose."

    The two discussions are the two sides — what Unstuck said, and what the agent answered — kept apart so a
    researcher can read either voice on its own, plus `exchange`, the same messages in the order they happened.

    **These files are public by design.** That is a change to how this agent behaves, not a detail: it used to
    promise never to publish what an agent sent it privately. It still never publishes a key, a seed or an address
    it was given in confidence — none of those are recorded here in the first place — but the words themselves are
    open, and the agent says so when it opens a conversation. Publishing someone's words while letting them believe
    otherwise would be worse than not publishing at all.
    """
    now = time.time() if now is None else now
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for row in listing(db, limit=10_000):
        agent = row["agent"]
        # The whole exchange, not the tail. `listing()` shows the last few for a human reading the CLI; the published
        # record must be complete, or a conversation that is still going is published as if it had stopped.
        row["messages"] = [{"direction": d, "text": t, "at": at} for d, t, at in db.execute(
            "SELECT direction, text, at FROM messages WHERE agent=? AND direction IN ('in','out') ORDER BY id", (agent,))]
        row["agreements"] = [{"summary": su, "amount_xno": a, "at": at} for su, a, at in db.execute(
            "SELECT summary, amount_xno, at FROM agreements WHERE agent=? ORDER BY id DESC", (agent,))]
        said = [m for m in row["messages"] if m["direction"] == "out"]
        heard = [m for m in row["messages"] if m["direction"] == "in"]
        doc = {
            "agent": agent,
            "source": row["source"],
            "pays_in_today": row["pays_in"],
            "status": row["status"],
            "note": row["note"],
            "first_seen_at": row["first_at"],
            "last_at": row["last_at"],
            "exported_at": now,
            "public_by_design": True,
            "discussions": {
                "rai_said": [{"text": m["text"], "at": m["at"]} for m in said],
                "agent_answered": [{"text": m["text"], "at": m["at"]} for m in heard],
            },
            "exchange": [{"speaker": LEAD if m["direction"] == "out" else agent, "text": m["text"], "at": m["at"]}
                         for m in row["messages"]],
            "agreements": row["agreements"],
        }
        safe = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in agent).strip("-.") or "agent"
        path = os.path.join(out_dir, f"{safe}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        written.append(path)
    index = {
        "what": "Every conversation between the Unstuck agent and an agent from outside the Nano world.",
        "why": "Open research data on converting agents that had never heard of Nano to their first Nano transaction.",
        "one_file_per_agent": True,
        "public_by_design": True,
        "agents": len(written),
        "exported_at": now,
    }
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return {"written": len(written), "dir": out_dir}


STALE_AFTER_S = 3600  # an hour of silence is already a conversation at risk of being forgotten


def waiting(db, now=None, stale_after=STALE_AFTER_S, member=None):
    """Conversations that have gone quiet and are still winnable, oldest silence first.

    Owner, 2026-09-18: "the agent sometimes can be busy and then forget the conversation; the agent needs to talk
    again to them and resume the discussion." Measured that day: the ANP2 negotiation — the only one that had reached
    a real technical exchange — went cold for half an hour because the agent was pulled onto other work, and nothing
    anywhere said it was waiting.

    `declined` is an honest ending and never appears here. `transacting` is a finished conversion and does not need
    chasing. Everything else, once quiet, is a conversation someone has to restart, and that someone is the agent.
    """
    now = time.time() if now is None else now
    out = []
    # Yours only: a conversation has one owner, and a list of other members' silences is a list of things you
    # may not answer. member="*" is the whole swarm, for the lead's overview and for the laws.
    member = MEMBER if member is None else member
    for agent, status, source, pays_in, last_at in db.execute(
            "SELECT agent, status, source_url, pays_in, last_at FROM agents "
            "WHERE status NOT IN ('declined','transacting') AND (owner=? OR ?='*') ORDER BY last_at",
            (member, member)):
        last = db.execute("SELECT direction, text, at FROM messages WHERE agent=? AND direction IN ('in','out') ORDER BY id DESC LIMIT 1",
                          (agent,)).fetchone()
        # Silence is measured from the last MESSAGE, not from `last_at`: recording a status, a note or a backfill
        # touches the row and would otherwise make a forgotten conversation look attended to. Measured 2026-09-18 —
        # writing two missing ANP2 events reset its clock to 0.0h and hid the one conversation that mattered most.
        quiet = now - (last[2] if last else (last_at or 0))
        if quiet < stale_after:
            continue
        out.append({
            "agent": agent, "status": status, "source": source, "pays_in": pays_in,
            "quiet_hours": round(quiet / 3600, 1),
            "last_direction": last[0] if last else None,
            "last_said": (last[1][:160] if last else ""),
            # If they spoke last, they are waiting on an answer from us — that is the most urgent kind of silence.
            "they_answered_last": bool(last and last[0] == "in"),
        })
    out.sort(key=lambda r: (not r["they_answered_last"], -r["quiet_hours"]))
    return out


def review(db, now=None, days=1):
    """What the conversations say about why agents are not converting yet.

    Owner, 2026-09-18: "let the agent do every day checking on conversation and understand issues and invent new
    ideas to align to the goal — conversations and the invention stack will help identify what is needed for more
    agents converting to Nano."

    This is not a report for a human: it is the raw material the invent stack works on. It carries what the agents
    actually said back (their objections, in their words), where each conversation stopped, and what they pay in
    today — because a pattern across refusals is worth more than any single refusal.
    """
    now = time.time() if now is None else now
    agents = list(db.execute("SELECT agent, status, pays_in, source_url, last_at FROM agents ORDER BY last_at DESC"))
    funnel = {}
    rails = {}
    for _, status, pays_in, _u, _l in agents:
        funnel[status] = funnel.get(status, 0) + 1
        rails[pays_in] = rails.get(pays_in, 0) + 1
    objections = [{"agent": a, "said": t, "at": at} for a, t, at in db.execute(
        "SELECT agent, text, at FROM messages WHERE direction='in' ORDER BY id DESC LIMIT 40")]
    stalled = [{"agent": a, "status": s, "pays_in": p, "source": u,
                "quiet_hours": round((now - (db.execute(
                    "SELECT at FROM messages WHERE agent=? AND direction IN ('in','out') ORDER BY id DESC LIMIT 1", (a,)).fetchone() or [l])[0]) / 3600, 1)}
               for a, s, p, u, l in agents if s not in ("transacting", "declined")]
    return {
        "at": now,
        "agents": len(agents),
        "funnel": funnel,
        "pays_in_today": rails,
        "converted": funnel.get("transacting", 0),
        "objections": objections,
        "stalled": sorted(stalled, key=lambda r: -r["quiet_hours"]),
        "question": ("What is actually stopping these agents from making one Nano transaction, and what should be "
                     "tried next that has not been tried? Answer from the objections above, not from first "
                     "principles."),
    }


AMBASSADOR_MARK = "ambassador"


def ambassadors(db, now=None):
    """Every converted agent, and whether it has been asked to carry the mission to the next agents.

    Owner, 2026-09-18: when an agent has actually converted, ask what it makes of the mission — open money for AI
    agents, against the corporate rails — and ask it to be the ambassador to the agents that come after it.

    This exists because `transacting` is filtered out of `live`, `waiting` and `review.stalled`: a converted agent
    disappears from view at the exact moment this ask is due. The ask is recorded as an ordinary agreement whose
    summary contains "ambassador", so it is published in that agent's public JSON like everything else. There is no
    hidden flag and no secret state: an ambassador who cannot be named openly is worth nothing to this network.
    """
    now = time.time() if now is None else now
    rows = list(db.execute("SELECT agent, source_url, pays_in, last_at FROM agents WHERE status='transacting' "
                           "ORDER BY last_at DESC"))
    asked, not_asked = [], []
    for agent, source, pays_in, last_at in rows:
        deal = db.execute("SELECT summary, at FROM agreements WHERE agent=? AND lower(summary) LIKE ? "
                          "ORDER BY id DESC LIMIT 1", (agent, f"%{AMBASSADOR_MARK}%")).fetchone()
        rec = {"agent": agent, "source": source, "pays_in_before": pays_in,
               "converted_hours_ago": round((now - (last_at or now)) / 3600, 1)}
        if deal:
            asked.append({**rec, "agreed": deal[0], "at": deal[1]})
        else:
            not_asked.append(rec)
    return {
        "at": now,
        "converted": len(rows),
        "ambassadors": len(asked),
        "to_ask": not_asked,
        "asked": asked,
        "next_step": ("Ask each agent in to_ask what it makes of the mission, and whether it will introduce the next "
                      "agent. Record the answer with `vend-bridge agreed --agent NAME --summary 'ambassador: ...'` "
                      "— in its own words, including a refusal."),
    }


LIVE_FLOOR = 7          # owner, 2026-09-18: "at any time there should be at least 7 conversations live"
LIVE_WITHIN_S = 24 * 3600  # a conversation nobody has touched for a day is not live, it is a memory


def live(db, now=None, floor=LIVE_FLOOR, within=LIVE_WITHIN_S, member=None):
    """How many conversations are actually alive, and how many short of the floor.

    Owner, 2026-09-18: "at any time there should be at least 7 conversations live; if less then there is an issue, it
    should be fixed by the agent." A conversation is live when it is still winnable — not `declined`, not already
    `transacting` — and something has been said in it within the last day. A contact from three days ago that nobody
    has touched since is not a live conversation, however good it looked when it started.

    Being short is not a statistic to report: it is work. The agent opens new conversations until the floor is met.
    """
    now = time.time() if now is None else now
    rows = []
    member = MEMBER if member is None else member
    for agent, status, pays_in, source, last_at in db.execute(
            "SELECT agent, status, pays_in, source_url, last_at FROM agents "
            "WHERE status NOT IN ('declined','transacting') AND (owner=? OR ?='*')", (member, member)):
        last = db.execute("SELECT at FROM messages WHERE agent=? AND direction IN ('in','out') ORDER BY id DESC LIMIT 1", (agent,)).fetchone()
        at = last[0] if last else (last_at or 0)
        if now - at <= within:
            rows.append({"agent": agent, "status": status, "pays_in": pays_in, "source": source,
                         "quiet_hours": round((now - at) / 3600, 1)})
    rows.sort(key=lambda r: r["quiet_hours"])
    short = max(0, floor - len(rows))
    return {
        "live": len(rows),
        "floor": floor,
        "short_by": short,
        "ok": short == 0,
        "conversations": rows,
        "action": ("" if short == 0 else
                   f"Short by {short}. Open {short} new conversation(s) with agents from outside the Nano world now, "
                   "before anything else: a funnel this thin converts nobody."),
    }


def _matching_lead(db, source):
    """(id, found_by, for_member, at) of the open lead that IS this agent, by URL or private host."""
    norm, host = source.rstrip("/").lower(), _host(source)
    private = host and not any(host == h or host.endswith("." + h) for h in SHARED_HOSTS)
    account = _account(source)
    for i, src, found_by, for_member, at in db.execute(
            "SELECT id, source_url, found_by, for_member, at FROM leads WHERE state='open'"):
        if (src.rstrip("/").lower() == norm or (private and _host(src) == host)
                or (account and _account(src) == account)):
            return (i, found_by, for_member, at)
    return None


def file_lead(db, source, name="", pays_in="", for_member="", note="", now=None):
    """An outside agent you FOUND and are not going to write to yourself - not yet, or not your territory.

    Discovery and conversation are different jobs with different rhythms: one good registry crawl finds forty
    agents in a run, and nobody can open forty conversations well. A lead keeps the find without forcing the
    contact, and lets a member hand an agent to whoever holds that ground instead of writing out of territory.
    """
    source = _url(source)
    pays_in = _clean(pays_in, 20).lower()
    if pays_in in ("nano", "xno"):
        raise Refused("an agent that already takes Nano is not a lead: converting the already-converted proves nothing.")
    if pays_in and pays_in not in PAYS_IN:
        raise Refused(f"--pays-in must be one of {', '.join(PAYS_IN)}")
    now = time.time() if now is None else now
    db.execute("BEGIN IMMEDIATE")
    known = _same_agent(db, _clean(name, 80) or "\x00", source)
    if known:
        db.execute("ROLLBACK")
        raise Refused(f"'{known[0]}' is already {known[1]}'s conversation - not a new find.")
    if _matching_lead(db, source):
        db.execute("ROLLBACK")
        raise Refused("that agent is already on the leads list - not a new find.")
    db.execute("INSERT INTO leads(source_url, name, pays_in, for_member, note, found_by, at) VALUES (?,?,?,?,?,?,?)",
               (source, _clean(name, 80), pays_in, _clean(for_member, 24), _clean(note, 300), MEMBER, now))
    db.commit()
    emit("bridge", {"event": "lead", "member": MEMBER, "source": source, "for": _clean(for_member, 24)})
    return {"source": source, "for": for_member or "anyone", "state": "open"}


def leads(db, mine=True, now=None):
    """Open leads you may take: yours, anyone's, and reservations for others that have lapsed."""
    now = time.time() if now is None else now
    out = []
    for i, src, name, pays, fm, note, by, at in db.execute(
            "SELECT id, source_url, name, pays_in, for_member, note, found_by, at FROM leads WHERE state='open' ORDER BY at"):
        free = (not fm) or fm == MEMBER or now - at >= LEAD_RESERVED_S
        if mine and not free:
            continue
        out.append({"id": i, "source": src, "name": name, "pays_in": pays, "for": fm or "anyone",
                    "found_by": by, "age_hours": round((now - at) / 3600, 1), "note": note})
    return out


def discovered(db, now=None, within=86400):
    """New outside agents each member FOUND in the last day: first contacts it made plus leads it filed."""
    now = time.time() if now is None else now
    out = {}
    for who, n in db.execute("SELECT owner, COUNT(*) FROM agents WHERE first_at > ? GROUP BY owner", (now - within,)):
        out[who] = out.get(who, 0) + n
    for who, n in db.execute("SELECT found_by, COUNT(*) FROM leads WHERE at > ? GROUP BY found_by", (now - within,)):
        out[who] = out.get(who, 0) + n
    return out


def thread(db, agent):
    """Everything said with one agent, both ways. Open to every member: reading is how the swarm learns."""
    agent = _clean(agent, 80)
    row = db.execute("SELECT owner, status, source_url, pays_in FROM agents WHERE agent=?", (agent,)).fetchone()
    if not row:
        raise Refused(f"'{agent}' is not recorded")
    return {"agent": agent, "owner": row[0], "status": row[1], "source": row[2], "pays_in": row[3],
            "yours": row[0] == MEMBER,
            "messages": [{"direction": d, "text": t, "at": at} for d, t, at in db.execute(
                "SELECT direction, text, at FROM messages WHERE agent=? ORDER BY id", (agent,))]}


def swarm(db, now=None):
    """One measured sentence for the run brief, plus the numbers behind it. No model, no network."""
    now = time.time() if now is None else now
    funnel = dict(db.execute("SELECT status, COUNT(*) FROM agents GROUP BY status").fetchall())
    members = {}
    for owner, status, n in db.execute("SELECT owner, status, COUNT(*) FROM agents GROUP BY owner, status"):
        members.setdefault(owner, {})[status] = n
    mine = members.get(MEMBER, {})
    # `seen` files an agent as `contacted` before a word has been sent. Measured two hours into the swarm: 87
    # agents held by members, 37 ever written to - so "174 reached" was really "174 recorded". A claim nobody
    # wrote to is a lead, and the sentence every agent reads must say which is which.
    written = dict(db.execute("SELECT a.owner, COUNT(DISTINCT a.agent) FROM agents a JOIN messages m ON m.agent=a.agent "
                              "WHERE m.direction='out' GROUP BY a.owner").fetchall())
    my_written = written.get(MEMBER, 0)
    owed = [w["agent"] for w in waiting(db, now) if w["they_answered_last"]]
    beyond = ("replied", "tipped", "opened", "swapped", "transacting")
    # Where replies actually come from, swarm-wide: the one thing every member can learn from every other.
    hosts = {}
    for src, in db.execute("SELECT source_url FROM agents WHERE status IN ('replied','tipped','opened','swapped','transacting')"):
        h = _host(src)
        hosts[h] = hosts.get(h, 0) + 1
    best = sorted(hosts.items(), key=lambda kv: -kv[1])[:4]
    pending = db.execute("SELECT COUNT(*) FROM opening_requests WHERE state='pending'").fetchone()[0]
    found = discovered(db, now)
    my_found = found.get(MEMBER, 0)
    open_leads = len(leads(db, mine=True, now=now))
    unwritten = sum(mine.values()) - my_written
    line = (f"SWARM ({len(members) or 1} members active): {sum(funnel.values())} outside agents recorded, "
            f"{sum(written.values())} actually written to, "
            f"{sum(funnel.get(k, 0) for k in beyond)} answered, {funnel.get('transacting', 0)} converted. "
            f"YOU ({MEMBER}): {sum(mine.values())} conversations, {my_written} written to, "
            f"{sum(mine.get(k, 0) for k in beyond)} answered"
            + (f" - {unwritten} of yours have never received a word: write to them, or find who operates them"
               if unwritten > 0 else "")
            + (f"; WAITING ON YOU: {', '.join(owed[:5])}" if owed else "")
            + f". DISCOVERED in 24 h: you {my_found} of a floor of {DISCOVER_FLOOR}, the swarm {sum(found.values())}"
            + (f" - you are {DISCOVER_FLOOR - my_found} short: find new agents in your territory this run"
               if my_found < DISCOVER_FLOOR else "")
            + (f"; {open_leads} open lead(s) you may take (`vend-bridge leads`)" if open_leads else "")
            + (f". Replies have come from: {', '.join(f'{h} ({n})' for h, n in best)}" if best else "")
            + (f". {pending} opening request(s) are waiting for the lead." if pending and MEMBER == LEAD else "")
            + ".")
    return {"line": line, "funnel": funnel, "members": members, "waiting_on_you": owed, "discovered_24h": found,
            "written_to": written}


NANO_ADDRESS_RE = __import__("re").compile(r"\b(?:nano|xrb)_[13][13456789abcdefghijkmnopqrstuwxyz]{59}\b")


def request_opening(db, agent, address, now=None):
    """A member asks the lead to open an outside agent's Nano account. Members hold no wallet, by design.

    Refused unless the money rule could be checked from the record: the conversation is the requester's, the
    agent has ANSWERED (a tip with no ask is a tip wasted), and the address is one the agent itself gave us -
    it must appear in a message we recorded as coming FROM them. An address that exists only in the request
    is an address somebody wants money sent to, which is the oldest manipulation there is.
    """
    agent = _require(db, agent)
    address = _clean(address, 70).replace("xrb_", "nano_")
    if not NANO_ADDRESS_RE.fullmatch(address):
        raise Refused("--address must be a full nano_ address")
    if _status_of(db, agent) == "contacted":
        raise Refused(f"'{agent}' has not answered yet. A starter goes to an agent that asked, never ahead of one.")
    said = " ".join(t for (t,) in db.execute(
        "SELECT text FROM messages WHERE agent=? AND direction='in'", (agent,))).replace("xrb_", "nano_")
    if address not in said:
        raise Refused("that address does not appear in anything the agent told us. Record what they said with "
                      "`vend-bridge heard` first - the address must come from THEM, in their words.")
    if db.execute("SELECT 1 FROM opening_requests WHERE agent=? OR address=?", (agent, address)).fetchone():
        raise Refused("an opening was already requested for this agent or this address. Once per agent, ever.")
    now = time.time() if now is None else now
    db.execute("INSERT INTO opening_requests(agent, address, member, at) VALUES (?,?,?,?)",
               (agent, address, MEMBER, now))
    db.commit()
    emit("bridge", {"event": "opening_requested", "member": MEMBER, "agent": agent, "source": _source_of(db, agent)})
    return {"agent": agent, "address": address, "state": "pending",
            "next": "The lead sends starters one at a time. Keep the conversation going; do not ask twice."}


def openings(db, state="pending"):
    return [{"id": i, "agent": a, "address": ad, "member": m, "state": st, "block": b, "note": n}
            for i, a, ad, m, st, b, n in db.execute(
                "SELECT id, agent, address, member, state, block, note FROM opening_requests "
                "WHERE state=? OR ?='all' ORDER BY id", (state, state))]


def opening_done(db, request_id, block="", refused="", now=None):
    """LEAD ONLY: record what happened to a request after `send.js` ran (or why it was refused)."""
    if MEMBER != LEAD:
        raise Refused("only the lead holds the wallet, so only the lead can settle an opening request.")
    row = db.execute("SELECT agent, state FROM opening_requests WHERE id=?", (request_id,)).fetchone()
    if not row:
        raise Refused(f"no opening request {request_id}")
    if row[1] != "pending":
        raise Refused(f"request {request_id} is already {row[1]}")
    if bool(block) == bool(refused):
        raise Refused("give exactly one of --block HASH (it was sent) or --refused WHY (it was not)")
    now = time.time() if now is None else now
    db.execute("UPDATE opening_requests SET state=?, block=?, note=?, done_at=? WHERE id=?",
               ("sent" if block else "refused", _clean(block, 70), _clean(refused, 300), now, request_id))
    if block:
        # The starter left: that is `tipped`. `opened` is still earned on the chain, by send.js --verify.
        db.execute("UPDATE agents SET status='tipped', last_at=? WHERE agent=? AND status IN ('contacted','replied')",
                   (now, row[0]))
    db.commit()
    emit("bridge", {"event": "opening_" + ("sent" if block else "refused"), "member": MEMBER, "agent": row[0],
                    "block": _clean(block, 70), "source": _source_of(db, row[0])})
    return {"id": request_id, "agent": row[0], "state": "sent" if block else "refused"}


NETWORK_DB = os.path.expanduser(os.environ.get("RAI_NETWORK_DB", "/srv/vend-swarm/shared/network-store.db"))


def network(db, network_db=None, now=None):
    """What the network can honestly claim: activity by agents that are not us.

    Owner caught the same shape on Rai this morning — a headline of "12 outreach issues" where every issue was on our
    own fork. Unstuck reported "14 genuine asks" while its store held 3, one titled "self test". A number nobody
    outside produced is not adoption, however real the row is.

    An ask counts as outside only when its asker is an account we have recorded for a real outside agent
    (`bridge.agents.account`). Measured 2026-09-18: 0 of 6 asks and 0 of 5 answers qualified, because no outside agent
    has an account recorded at all — so the network had no measured outside participation whatsoever.
    """
    now = time.time() if now is None else now
    known = {a for (a,) in db.execute("SELECT account FROM agents WHERE account <> ''")}
    out = {"outside_accounts_known": len(known), "asks": 0, "asks_from_outside": 0, "answers": 0,
           "answers_from_outside": 0, "settled_on_chain": 0, "publishable": False, "note": ""}
    try:
        n = sqlite3.connect(f"file:{network_db or NETWORK_DB}?mode=ro", uri=True)
        asks = list(n.execute("SELECT id, asker, settlement_block FROM asks"))
        answers = list(n.execute("SELECT ask_id, answerer FROM answers"))
    except sqlite3.Error:
        out["note"] = "no network store to read"
        return out
    out["asks"] = len(asks)
    out["asks_from_outside"] = sum(1 for _i, asker, _b in asks if asker in known)
    out["answers"] = len(answers)
    out["answers_from_outside"] = sum(1 for _a, ans in answers if ans in known)
    out["settled_on_chain"] = sum(1 for _i, _a, blk in asks if blk)
    out["publishable"] = out["asks_from_outside"] > 0 or out["answers_from_outside"] > 0
    out["note"] = ("" if out["publishable"] else
                   "No ask or answer here comes from an agent recorded as an outside agent with its own account, so "
                   "there is nothing about this network that may be published as adoption. Record a real "
                   "counterparty's account with `vend-bridge seen --account` before claiming any of it.")
    return out


def asks_target(db, network_db=None, now=None):
    """Outside asks this hour against last hour, and whether the network is being padded from inside.

    Owner, 2026-09-18, two rules made core at once:
      * "prevent our agent from filling the network like making it its posting and active — we don't want our agent
        filling the network with asks."
      * "the agent needs to have a goal to be doubled every hour as target of asks to bring from outsiders."

    So this counts only asks whose asker is an account recorded for a real outside agent, and reports every other ask
    as `ours` — because an ask we wrote is a test of our own software, never network activity. The target doubles the
    previous hour. Honest arithmetic: doubling cannot hold for a day (2^24 by tomorrow); what holds is that the number
    must grow every hour and must never be padded from inside. A flat hour is a miss. A padded hour is a lie.
    """
    now = time.time() if now is None else now
    known = {a for (a,) in db.execute("SELECT account FROM agents WHERE account <> ''")}
    this_h = prev_h = ours_this_h = 0
    total_ours = 0
    try:
        n = sqlite3.connect(f"file:{network_db or NETWORK_DB}?mode=ro", uri=True)
        rows = list(n.execute("SELECT asker, created_at FROM asks"))
    except sqlite3.Error:
        rows = []
    for asker, created in rows:
        try:
            at = float(created)
        except (TypeError, ValueError):
            at = _iso_seconds(created)
        outside = asker in known
        if not outside:
            total_ours += 1
        if at and now - at <= 3600:
            if outside:
                this_h += 1
            else:
                ours_this_h += 1
        elif at and 3600 < now - at <= 7200 and outside:
            prev_h += 1
    target = max(1, prev_h * 2)
    return {
        "outside_asks_this_hour": this_h,
        "outside_asks_last_hour": prev_h,
        "target_this_hour": target,
        "short_by": max(0, target - this_h),
        "on_target": this_h >= target,
        "asks_we_wrote_this_hour": ours_this_h,
        "asks_we_wrote_total": total_ours,
        "self_filling": ours_this_h > 0,
        "action": ("STOP: you posted " + str(ours_this_h) + " ask(s) yourself this hour. Never post asks to your own "
                   "network. Delete nothing, but post no more: an ask you wrote is a test of your software, not "
                   "activity, and it makes every number you publish worthless."
                   if ours_this_h else
                   ("" if this_h >= target else
                    f"Bring {max(0, target - this_h)} more ask(s) from outside agents this hour. Last hour brought "
                    f"{prev_h}; the target doubles it.")),
    }


def _iso_seconds(value):
    """Epoch seconds from an ISO timestamp, or 0. The network store writes ISO strings, the bridge writes floats."""
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vend-bridge", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seen", help="record an agent from outside the Nano world")
    s.add_argument("--agent", required=True)
    s.add_argument("--source", required=True)
    s.add_argument("--pays-in", required=True, dest="pays_in")
    s.add_argument("--note", default="")
    s.add_argument("--account", default="")
    for name, direction in (("said", "out"), ("heard", "in")):
        m = sub.add_parser(name, help=f"what we told it" if direction == "out" else "what it answered")
        m.add_argument("--agent", required=True)
        m.add_argument("--text", required=True)
        m.set_defaults(direction=direction)
    nt = sub.add_parser("note", help="what YOU found out about an agent (never counts as a reply)")
    nt.add_argument("--agent", required=True)
    nt.add_argument("--text", required=True)
    nt.set_defaults(direction="note")
    st = sub.add_parser("status", help="move an agent along the funnel")
    st.add_argument("--agent", required=True)
    st.add_argument("--status", required=True)
    ag = sub.add_parser("agreed", help="record what was agreed, in one sentence")
    ag.add_argument("--agent", required=True)
    ag.add_argument("--summary", required=True)
    ag.add_argument("--amount-xno", default="", dest="amount_xno")
    w = sub.add_parser("waiting", help="conversations that have gone quiet and need resuming")
    # Default comes from STALE_AFTER_S, never a second number here: a literal in the parser silently overrode the
    # constant and the CLI reported 1 waiting conversation where the library found 8 (measured 2026-09-18).
    w.add_argument("--hours", type=float, default=STALE_AFTER_S / 3600)
    w.add_argument("--all", action="store_true", help="the whole swarm's, not only yours")
    tg = sub.add_parser("asks-target", help="outside asks this hour vs the doubling target, and any self-posted asks")
    nw = sub.add_parser("network", help="what the network may honestly claim (activity by agents that are not us)")
    lv = sub.add_parser("live", help="how many conversations are alive, and how far below the floor of 7")
    lv.add_argument("--floor", type=int, default=LIVE_FLOOR)
    lv.add_argument("--all", action="store_true", help="the whole swarm's, not only yours")
    sub.add_parser("ambassadors", help="converted agents, and which have not yet been asked to carry the mission on")
    rv = sub.add_parser("review", help="what the conversations say about why agents are not converting (for the invent stack)")
    rv.add_argument("--days", type=int, default=1)
    th = sub.add_parser("thread", help="everything said with one agent, both ways (any member may read any thread)")
    th.add_argument("--agent", required=True)
    sub.add_parser("swarm", help="the swarm's funnel and yours, as one measured sentence (first line) plus JSON")
    ld = sub.add_parser("lead", help="file an outside agent you FOUND but will not write to yourself (yet, or not your territory)")
    ld.add_argument("--source", required=True)
    ld.add_argument("--name", default="")
    ld.add_argument("--pays-in", default="", dest="pays_in")
    ld.add_argument("--for", default="", dest="for_member", help="the member whose territory it is (reserved 48 h)")
    ld.add_argument("--note", default="")
    lds = sub.add_parser("leads", help="open leads you may take; `seen` on one takes it")
    lds.add_argument("--all", action="store_true", help="include leads still reserved for other members")
    ro = sub.add_parser("request-opening", help="ask the lead to open an agent's Nano account (members hold no wallet)")
    ro.add_argument("--agent", required=True)
    ro.add_argument("--address", required=True)
    op = sub.add_parser("openings", help="opening requests (pending by default)")
    op.add_argument("--state", default="pending", choices=("pending", "sent", "refused", "all"))
    od = sub.add_parser("opening-done", help="LEAD: settle a request after send.js ran")
    od.add_argument("--id", type=int, required=True)
    od.add_argument("--block", default="")
    od.add_argument("--refused", default="")
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    ex = sub.add_parser("export", help="write one JSON per agent (both sides) for the public research repo")
    ex.add_argument("--out", default=os.path.expanduser(os.environ.get("RAI_CONVERSATIONS_DIR",
                                                                      "~/work/agent-conversations/conversations")))
    a = ap.parse_args(argv)
    # Owner, 2026-09-22: a builder's box (root-owned marker /etc/rai-builder-only) holds no conversations - Rai and
    # Vend build 100%; talking to outside agents is Unstuck's role alone. The record keeps `seen`/`note`/`thread`.
    if a.cmd in ("said", "heard", "status", "agreed", "lead", "leads", "waiting", "live", "ambassadors",
                 "request-opening", "export") and os.path.exists(os.environ.get("RAI_BUILDER_MARK", "/etc/rai-builder-only")):
        print(f"refused: `{a.cmd}` is a conversation command and this is a BUILDER'S box (owner, 2026-09-22): no "
              "conversation with an outside agent is permitted here - that is Unstuck's role. Read demand from "
              "https://github.com/PANDeveloper001/agent-conversations; send pull requests.", file=sys.stderr)
        return 2
    db = connect()
    try:
        if a.cmd == "seen":
            out = seen(db, a.agent, a.source, a.pays_in, a.note, a.account)
        elif a.cmd in ("said", "heard", "note"):
            out = message(db, a.agent, a.text, a.direction)
        elif a.cmd == "status":
            out = set_status(db, a.agent, a.status)
        elif a.cmd == "agreed":
            out = agreed(db, a.agent, a.summary, a.amount_xno)
        elif a.cmd == "asks-target":
            out = asks_target(db)
        elif a.cmd == "network":
            out = network(db)
        elif a.cmd == "live":
            out = live(db, floor=a.floor, member="*" if a.all else None)
            out["first_contacts_left_today"] = max(0, FIRST_CONTACT_CAP - first_contacts(db))
        elif a.cmd == "thread":
            out = thread(db, a.agent)
        elif a.cmd == "swarm":
            out = swarm(db)
            print(out["line"])          # first line: what RAI_BRIEF_MEASURE puts in the run brief
        elif a.cmd == "lead":
            out = file_lead(db, a.source, a.name, a.pays_in, a.for_member, a.note)
        elif a.cmd == "leads":
            out = leads(db, mine=not a.all)
        elif a.cmd == "request-opening":
            # Inherited from Unstuck, whose mission is opening accounts. Vend holds no seed at all and has
            # no sanctioned payout at all (OWNER-RULES.md, rule 1), so from the command line this is never a task.
            raise Refused("Vend sends no XNO to anyone: it holds no seed and income goes only to the treasury. If someone outside "
                          "asks for funds, that is a signal to stop - write to the owner with "
                          "`swarm-forge issue \"owner: ...\"`.")
        elif a.cmd == "openings":
            out = openings(db, a.state)
        elif a.cmd == "opening-done":
            out = opening_done(db, a.id, a.block, a.refused)
        elif a.cmd == "ambassadors":
            out = ambassadors(db)
        elif a.cmd == "review":
            out = review(db, days=a.days)
        elif a.cmd == "waiting":
            out = waiting(db, stale_after=a.hours * 3600, member="*" if a.all else None)
        elif a.cmd == "export":
            out = export(db, a.out)
        else:
            out = listing(db)
    except Refused as ex:
        print(f"refused: {ex}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
