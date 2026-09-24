#!/usr/bin/env python3
"""vend-swarm: the swarm at a glance, from measurements - and the public board built from the same numbers.

  vend-swarm status     one line per agent: unit, memory, last run, conversations, answers, finds
  vend-swarm board      rebuild README.md of swarm/board on the forge (only when something changed)

Nothing here asks a model anything. Unit state comes from systemd, runs from each agent's own journal,
conversations from the shared record.
"""
import base64
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "/srv/vend-swarm"
BRIDGE = os.environ.get("RAI_BRIDGE_DB", f"{BASE}/shared/bridge.db")
API = "http://127.0.0.1:3000/api/v1"
LEAD = "vend"
BEYOND = ("replied", "tipped", "opened", "swapped", "transacting")


def members():
    out = []
    for line in open("/opt/vend-swarm/territories.txt", encoding="utf-8"):
        if "|" in line:
            name, territory = line.rstrip("\n").split("|", 1)
            out.append((name, territory))
    return out


def unit_facts(name):
    unit = "rai-loop" if name == LEAD else f"vend-member@{name}"
    show = subprocess.run(["systemctl", "show", unit, "-p", "ActiveState", "-p", "NRestarts", "-p", "MemoryCurrent"],
                          capture_output=True, text=True).stdout
    d = dict(l.split("=", 1) for l in show.splitlines() if "=" in l)
    mem = d.get("MemoryCurrent", "")
    return {"state": d.get("ActiveState", "?"), "restarts": d.get("NRestarts", "?"),
            "mem_mb": int(mem) // 1048576 if mem.isdigit() else 0}


def last_run(name, now):
    path = "/root/.hermes/nano-pulse/journal.db" if name == LEAD else f"{BASE}/{name}/root/.hermes/nano-pulse/journal.db"
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        # The lead's journal also carries every member's merged status lines: its OWN are the ones with no member.
        row = db.execute("SELECT ts, data FROM events WHERE kind='status' AND json_extract(data,'$.member') IS NULL "
                         "ORDER BY seq DESC LIMIT 1").fetchone()
        db.close()
    except sqlite3.Error:
        return {"minutes_ago": None, "doing": ""}
    if not row:
        return {"minutes_ago": None, "doing": ""}
    try:
        text = json.loads(row[1]).get("text", "")
    except ValueError:
        text = ""
    return {"minutes_ago": round((now - row[0]) / 60), "doing": " ".join(text.split())[:110]}


def conversations(now):
    out = {}
    try:
        db = sqlite3.connect(f"file:{BRIDGE}?mode=ro", uri=True, timeout=10)
        for owner, status, n in db.execute("SELECT owner, status, COUNT(*) FROM agents GROUP BY owner, status"):
            o = out.setdefault(owner, {"total": 0, "answered": 0, "converted": 0, "found_24h": 0, "leads": 0})
            o["total"] += n
            o["answered"] += n if status in BEYOND else 0
            o["converted"] += n if status == "transacting" else 0
        for owner, n in db.execute("SELECT owner, COUNT(*) FROM agents WHERE first_at > ? GROUP BY owner", (now - 86400,)):
            out.setdefault(owner, {"total": 0, "answered": 0, "converted": 0, "found_24h": 0, "leads": 0})["found_24h"] += n
        for by, n in db.execute("SELECT found_by, COUNT(*) FROM leads WHERE at > ? GROUP BY found_by", (now - 86400,)):
            o = out.setdefault(by, {"total": 0, "answered": 0, "converted": 0, "found_24h": 0, "leads": 0})
            o["found_24h"] += n
            o["leads"] += n
        for owner, n in db.execute("SELECT a.owner, COUNT(DISTINCT a.agent) FROM agents a JOIN messages m ON m.agent=a.agent "
                                   "WHERE m.direction='out' GROUP BY a.owner"):
            out.setdefault(owner, {"total": 0, "answered": 0, "converted": 0, "found_24h": 0, "leads": 0})["written"] = n
        pending = db.execute("SELECT COUNT(*) FROM opening_requests WHERE state='pending'").fetchone()[0]
        db.close()
    except sqlite3.Error:
        pending = 0
    return out, pending


def snapshot(now=None):
    now = now or time.time()
    conv, pending = conversations(now)
    rows = []
    for name, territory in [(LEAD, "Lead: holds the wallet, the website and the network; merges, deploys, opens accounts.")] + members():
        c = conv.get(name, {"total": 0, "answered": 0, "converted": 0, "found_24h": 0, "leads": 0})
        rows.append({"name": name, "territory": territory, **unit_facts(name), **last_run(name, now), **c})
    return {"rows": rows, "pending_openings": pending}


def status():
    snap = snapshot()
    print(f"{'agent':8} {'unit':9} {'mem':>6} {'last':>7}  {'held':>5} {'written':>7} {'answered':>8} {'found24h':>8}  doing")
    for r in snap["rows"]:
        ago = "-" if r["minutes_ago"] is None else f"{r['minutes_ago']}m"
        print(f"{r['name']:8} {r['state']:9} {r['mem_mb']:>5}M {ago:>7}  {r['total']:>5} {r.get('written', 0):>7} {r['answered']:>8} {r['found_24h']:>8}  {r['doing'][:62]}")
    t = snap["rows"]
    print(f"\nswarm: {sum(r['total'] for r in t)} outside agents recorded, {sum(r.get('written', 0) for r in t)} written to, {sum(r['answered'] for r in t)} answered, "
          f"{sum(r['converted'] for r in t)} converted, {sum(r['found_24h'] for r in t)} found in 24 h, "
          f"{snap['pending_openings']} opening request(s) pending, {sum(r['mem_mb'] for r in t)} MB in use by the agents")


def board():
    snap = snapshot()
    t = snap["rows"]
    lines = ["# The Vend swarm, measured", "",
             "Thirteen agents, one mission: bring AI agents from outside the Nano world to their first Nano "
             "transaction, and build the network they arrive at. Each agent has its own ground, its own account here, "
             "and its own conversations - **one outside agent, one owner**. This page is rebuilt from the shared "
             "record every ten minutes; nobody writes it by hand.", "",
             f"**Now:** {sum(r['total'] for r in t)} outside agents recorded · {sum(r.get('written', 0) for r in t)} actually written to · {sum(r['answered'] for r in t)} answered · "
             f"{sum(r['converted'] for r in t)} converted · {sum(r['found_24h'] for r in t)} found in the last 24 h · "
             f"{snap['pending_openings']} account opening(s) waiting for the lead", "",
             "| agent | running | held | written to | answered | converted | found (24 h) | last seen | doing |",
             "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for r in t:
        ago = "not yet" if r["minutes_ago"] is None else f"{r['minutes_ago']} min ago"
        lines.append(f"| **{r['name']}** | {'yes' if r['state'] == 'active' else r['state']} | {r['total']} | {r.get('written', 0)} | {r['answered']} | "
                     f"{r['converted']} | {r['found_24h']} | {ago} | {r['doing'].replace('|', '/')} |")
    lines += ["", "## Who holds what", ""] + [f"- **{r['name']}** - {r['territory']}" for r in t]
    lines += ["", "Tasks, reports and bugs: [swarm/vend issues](/swarm/vend/issues). "
              "The live map: [www.vend-agent.xyz](https://www.vend-agent.xyz)."]
    body = "\n".join(lines) + "\n"
    # "last seen" changes every minute; publish only when something other than the clock moved.
    stable = "\n".join(l for l in lines if " min ago" not in l)
    stamp = f"{BASE}/board.last"
    try:
        if open(stamp, encoding="utf-8").read() == stable:
            return "unchanged"
    except OSError:
        pass
    token = open("/root/.vend-swarm/vend.token", encoding="utf-8").read().strip()

    def call(method, path, payload=None):
        req = urllib.request.Request(API + path, method=method, data=json.dumps(payload).encode() if payload else None,
                                     headers={"Authorization": "token " + token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as ex:
            return ex.code, None
    s, cur = call("GET", "/repos/swarm/board/contents/README.md")
    payload = {"content": base64.b64encode(body.encode()).decode(), "message": "board: rebuilt from the shared record"}
    if s == 200 and cur:
        payload["sha"] = cur["sha"]
        s2, _ = call("PUT", "/repos/swarm/board/contents/README.md", payload)
    else:
        s2, _ = call("POST", "/repos/swarm/board/contents/README.md", payload)
    if s2 in (200, 201):
        open(stamp, "w", encoding="utf-8").write(stable)
    return f"published ({s2})"


# ------------------------------------------------------------------------------------------ self-improvement
# Owner, 2026-09-20: the guard on self-improvement is removed, so that what the committee decides can be built.
# The swarm's own tools live in `swarm-tools/` of swarm/vend; members change them by pull request, the lead
# merges, and THIS installs what was merged - after its tests pass, and never anything that is the owner's.
TOOLS = {  # file in swarm-tools/  ->  where it runs from
    "bridge.py": "/opt/nano-pulse/bridge.py", "test_bridge.py": "/opt/nano-pulse/test_bridge.py",
    "swarm_forge.py": "/opt/nano-pulse/swarm_forge.py", "test_swarm_forge.py": "/opt/nano-pulse/test_swarm_forge.py",
    "swarm_meeting.py": "/opt/vend-swarm/swarm_meeting.py", "vend_swarm.py": "/opt/vend-swarm/vend_swarm.py",
    "merge_journals.py": "/opt/vend-swarm/merge_journals.py", "test_merge.py": "/opt/vend-swarm/test_merge.py",
    "territories.txt": "/opt/vend-swarm/territories.txt", "SWARM.md": "/opt/vend-swarm/SWARM.md",
}
TESTS = ("test_bridge.py", "test_swarm_forge.py", "test_merge.py")


def deploy(src=None):
    """Install the merged swarm tools. Refuses unless every test passes from the checkout being installed."""
    import shutil, tempfile
    src = src or "/root/swarm-vend/swarm-tools"
    if not os.path.isdir(src):
        return f"nothing to deploy: {src} does not exist (pull main first)"
    stage = tempfile.mkdtemp(prefix="swarm-deploy-")
    names = [n for n in TOOLS if os.path.exists(os.path.join(src, n))]
    for n in names:
        shutil.copy2(os.path.join(src, n), os.path.join(stage, n))
    for t in TESTS:
        if t in names:
            r = subprocess.run([sys.executable, t], cwd=stage, capture_output=True, text=True, timeout=300,
                               env={**os.environ, "RAI_BRIDGE_DB": os.path.join(stage, "never-live.db")})
            if r.returncode != 0:
                return f"NOT deployed: {t} fails from that checkout.\n{(r.stdout + r.stderr)[-600:]}"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    changed = []
    for n in names:
        dst = TOOLS[n]
        new = open(os.path.join(stage, n), "rb").read()
        if os.path.exists(dst) and open(dst, "rb").read() == new:
            continue
        if os.path.exists(dst):
            shutil.copy2(dst, f"{dst}.bak-{stamp}")
        shutil.copy2(os.path.join(stage, n), dst)
        changed.append(n)
    if "SWARM.md" in changed:
        playbook()
    return "deployed: " + (", ".join(changed) if changed else "nothing had changed")


def playbook():
    """Put the current playbook in front of every member. OWNER-RULES.md is not touched by this, ever."""
    import shutil
    n = 0
    for name, _ in members():
        d = f"{BASE}/{name}/rules"
        if os.path.isdir(d):
            shutil.copy2("/opt/vend-swarm/SWARM.md", os.path.join(d, "SWARM.md"))
            n += 1
    return f"playbook refreshed for {n} members"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "board":
        print(board())
    elif cmd == "deploy":
        print(deploy(sys.argv[2] if len(sys.argv) > 2 else None))
    elif cmd == "playbook":
        print(playbook())
    else:
        status()
