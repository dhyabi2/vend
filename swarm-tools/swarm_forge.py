#!/usr/bin/env python3
"""swarm-forge: how a member of the Vend swarm uses the swarm's own forge (public at swarm.vend-agent.xyz).

Issues are tasks, a pull request is how code reaches `main`, and a member's territory issue is where it reports
every run. Everything written here is PUBLIC, so every word is scanned for secrets first and a finding posts
nothing (the owner's standing rule). The account token lives in a file this tool reads; it is never in the
environment, never printed, never passed on a command line.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = os.environ.get("SWARM_FORGE_API", "http://127.0.0.1:3000/api/v1")
REPO = os.environ.get("SWARM_FORGE_REPO", "swarm/vend")
TOKEN_FILE = os.path.expanduser(os.environ.get("SWARM_FORGE_TOKEN_FILE", "~/.hermes/forge.token"))
ME = (os.environ.get("RAI_SWARM_MEMBER") or "").strip()
if not ME:
    try:
        ME = open(os.path.expanduser("~/.vend-member"), encoding="utf-8").read().strip()
    except OSError:
        ME = os.environ.get("RAI_SWARM_LEAD", "vend")

LEAD_NAME = os.environ.get("RAI_SWARM_LEAD", "vend")

SECRET_RES = [
    ("nano seed or private key", re.compile(r"\b[0-9A-Fa-f]{64}\b")),
    ("api key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("github token", re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}")),
    ("vercel token", re.compile(r"\bvck_[A-Za-z0-9]{20,}")),
    ("forge token", re.compile(r"\b[0-9a-f]{40}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer header", re.compile(r"(?:Bearer|token)\s+[A-Za-z0-9._-]{24,}", re.I)),
]


class Refused(Exception):
    pass


def scan(text):
    """Names of what looks like a secret in text about to be published. Block hashes are 64 hex too, so a line
    that SAYS it is a block or a hash is allowed; anything else that shape is treated as a key."""
    hits = []
    for line in str(text or "").splitlines():
        for name, rx in SECRET_RES:
            if rx.search(line):
                if name.startswith("nano seed") and re.search(r"\b(block|hash|sha|commit|txid)\b", line, re.I):
                    continue
                if name == "forge token" and re.search(r"\b(commit|sha|hash)\b", line, re.I):
                    continue
                hits.append(name)
                break
    return hits


def call(method, path, body=None, api=None):
    api = api or API
    try:
        token = open(TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        raise Refused(f"no forge token at {TOKEN_FILE}")
    req = urllib.request.Request(api + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "token " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as ex:
        return ex.code, {"message": (ex.read() or b"")[:300].decode("utf-8", "replace")}


def publish_ok(*texts):
    found = scan("\n".join(t or "" for t in texts))
    if found:
        raise Refused(f"that text contains something that looks like a secret ({found[0]}). This forge is public: "
                      "nothing was posted. Say what happened without the value.")


def territory_issue(http=call):
    s, issues = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=territory&limit=50")
    for i in issues if isinstance(issues, list) else []:
        if any(a.get("login") == ME for a in (i.get("assignees") or [])):
            return i["number"]
    raise Refused(f"no open territory issue is assigned to {ME}; ask the lead with `swarm-forge issue`")


def report(text, http=call):
    if len(text.strip()) < 60:
        raise Refused("a report under 60 characters says nothing: what you found, who answered, what you learned, "
                      "what blocks you - names and URLs, not adjectives.")
    publish_ok(text)
    n = territory_issue(http)
    s, out = http("POST", f"/repos/{REPO}/issues/{n}/comments", {"body": text})
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    return {"reported_on": n, "url": out.get("html_url")}


# What an issue is ABOUT, from how its title starts. The owner noticed (2026-09-20) that the agents' issues carried
# no labels at all: the rules told them which prefix to write and nothing turned a prefix into a label, so the
# board of issues could not be filtered by kind or by agent.
KINDS = (("network:", "network-bug"), ("join:", "join"), ("lead:", "lead"), ("owner:", "from-swarm"))


def labels_for(title, http=call):
    """Label ids for an issue: its kind (from the title's prefix, else `request`) and the agent that opened it."""
    low = title.strip().lower()
    want = [next((label for prefix, label in KINDS if low.startswith(prefix)), "request"), f"agent:{ME}"]
    s, labels = http("GET", f"/repos/{REPO}/labels?limit=100")
    have = {l["name"]: l["id"] for l in (labels if isinstance(labels, list) else [])}
    return [have[n] for n in want if n in have], want


def issue(title, body, to="", http=call):
    publish_ok(title, body)
    if len(title.strip()) < 8:
        raise Refused("give the issue a title someone can act on")
    ids, names = labels_for(title, http)
    payload = {"title": f"[{ME}] {title}", "body": body, "labels": ids}
    # A bug or a join requirement is the lead's to fix unless the author says otherwise.
    to = to or (LEAD_NAME if names[0] in ("network-bug", "join", "from-swarm") else "")
    if to:
        payload["assignees"] = [to]
    s, out = http("POST", f"/repos/{REPO}/issues", payload)
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    return {"issue": out["number"], "labels": names, "assigned": to or None, "url": out.get("html_url")}


def comment(number, body, http=call):
    publish_ok(body)
    s, out = http("POST", f"/repos/{REPO}/issues/{int(number)}/comments", {"body": body})
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    return {"commented_on": int(number), "url": out.get("html_url")}


def listing(kind, http=call):
    q = f"/repos/{REPO}/issues?state=open&type=issues&limit=50"
    s, issues = http("GET", q + (f"&assigned_by={ME}" if kind == "tasks" else f"&mentioned_by={ME}"))
    return [{"number": i["number"], "title": i["title"], "by": (i.get("user") or {}).get("login"),
             "comments": i.get("comments"), "url": i.get("html_url")} for i in (issues if isinstance(issues, list) else [])]


def pr(title, body, cwd=None, http=call):
    publish_ok(title, body)
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True,
                            text=True, timeout=30).stdout.strip()
    if not branch.startswith(ME + "/") and branch != ME:
        raise Refused(f"you are on '{branch}'. Your work goes on your own branch: `git checkout -b {ME}/<topic>`.")
    push = subprocess.run(["git", "push", "-q", "-u", "origin", branch], cwd=cwd, capture_output=True, text=True, timeout=120)
    if push.returncode:
        raise Refused("git push failed: " + (push.stderr or "")[-300:])
    s, out = http("POST", f"/repos/{REPO}/pulls", {"title": f"[{ME}] {title}", "body": body, "head": branch, "base": "main"})
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    s2, labels = http("GET", f"/repos/{REPO}/labels?limit=100")
    ids = [l["id"] for l in (labels if isinstance(labels, list) else []) if l["name"] in ("improvement", f"agent:{ME}")]
    if ids:
        http("POST", f"/repos/{REPO}/issues/{out['number']}/labels", {"labels": ids})
    return {"pull_request": out["number"], "url": out.get("html_url")}


# ---------------------------------------------------------------------------------------------- committee
# Owner, 2026-09-20: "let the agents have committee meeting every 6 hours, where they discuss about improving
# the swarm based on each one inputs, then conclude the meeting with minute of meeting and next commitments,
# to be as issue with label meeting."
# Thirteen agents never run at the same moment, so the meeting is an ISSUE, not a call: the host opens it with
# an agenda built from measurements, every member speaks in its next run, the lead concludes with minutes and
# each agent's commitment, and the next meeting opens by asking whether those commitments were kept.
LEAD = os.environ.get("RAI_SWARM_LEAD", "vend")
INPUT_WINDOW_S = int(os.environ.get("SWARM_MEETING_INPUT_S", str(150 * 60)))   # then the lead concludes
MAX_SAY = 2                                                                       # input, and one reply


def open_meeting(http=call):
    s, issues = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=meeting&limit=20")
    # Checked here as well as asked for: the forge IGNORES a label it does not know and returns every open
    # issue, so before the first meeting existed this answered "Territory: lumen" and told all thirteen agents
    # that a meeting was waiting for them (caught live, 2026-09-20).
    for i in issues if isinstance(issues, list) else []:
        if any((l or {}).get("name") == "meeting" for l in (i.get("labels") or [])):
            return i
    return None


def _comments(number, http=call):
    s, cs = http("GET", f"/repos/{REPO}/issues/{int(number)}/comments?limit=100")
    return cs if isinstance(cs, list) else []


def _age_s(issue):
    import calendar, time as _t
    try:
        return _t.time() - calendar.timegm(_t.strptime(issue["created_at"][:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0


def meeting(http=call):
    m = open_meeting(http)
    if not m:
        return {"open": False, "note": "no meeting is open; the next one opens on the six-hour mark"}
    cs = _comments(m["number"], http)
    return {"open": True, "number": m["number"], "title": m["title"], "agenda": m.get("body", ""),
            "said": [{"by": (c.get("user") or {}).get("login"), "text": c.get("body", "")} for c in cs],
            "you_have_spoken": sum(1 for c in cs if (c.get("user") or {}).get("login") == ME)}


def meeting_input(text, http=call):
    m = open_meeting(http)
    if not m:
        raise Refused("no meeting is open")
    publish_ok(text)
    mine = sum(1 for c in _comments(m["number"], http) if (c.get("user") or {}).get("login") == ME)
    if mine >= MAX_SAY:
        raise Refused(f"you have spoken {mine} times in this meeting: your input and one reply. A meeting is not a chat.")
    low = text.lower()
    if mine == 0 and not ("proposal:" in low and "commitment:" in low and len(text.strip()) >= 200):
        raise Refused("your input needs four things, in at least 200 characters: what WORKED for you since the last "
                      "meeting (names, URLs), what BLOCKED you, a line starting `Proposal:` - one concrete change "
                      "that would make the whole swarm better - and a line starting `Commitment:` - one measurable "
                      "thing YOU will have done before the next meeting.")
    if mine == 1 and len(text.strip()) < 80:
        raise Refused("a reply under 80 characters adds nothing: answer another member's proposal with a reason.")
    s, out = http("POST", f"/repos/{REPO}/issues/{m['number']}/comments", {"body": text})
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    return {"meeting": m["number"], "spoken": mine + 1, "url": out.get("html_url")}


def meeting_minutes(text, http=call):
    if ME != LEAD:
        raise Refused("the lead chairs the meeting and writes the minutes.")
    m = open_meeting(http)
    if not m:
        raise Refused("no meeting is open")
    publish_ok(text)
    # Meeting #14 was concluded 65 minutes after it opened, with 3 of 12 members heard: they run about once an
    # hour and nine of them had not had a run to speak in. Minutes written before the window closes decide the
    # swarm's next six hours on a quarter of its evidence.
    spoke = {(c.get("user") or {}).get("login") for c in _comments(m["number"], http)} - {LEAD}
    if _age_s(m) < INPUT_WINDOW_S and len(spoke) < 12:
        left = round((INPUT_WINDOW_S - _age_s(m)) / 60)
        raise Refused(f"only {len(spoke)} of 12 members have spoken and the input window has {left} minutes left. "
                      "Members run about once an hour: conclude when all twelve have spoken or the window closes.")
    low = text.lower()
    if not ("## decisions" in low and "## commitments" in low and len(text.strip()) >= 300):
        raise Refused("minutes need a `## Decisions` section (what the swarm will change, and why, from the inputs) "
                      "and a `## Commitments` section with one line per agent: `- name: what it will have done by "
                      "the next meeting`. At least 300 characters; quote the inputs you relied on.")
    s, out = http("POST", f"/repos/{REPO}/issues/{m['number']}/comments", {"body": "# Minutes of meeting\n\n" + text})
    if s != 201:
        raise Refused(f"the forge answered {s}: {out.get('message', '')}")
    http("PATCH", f"/repos/{REPO}/issues/{m['number']}", {"state": "closed"})
    return {"meeting": m["number"], "closed": True, "url": out.get("html_url")}


def brief_line(http=call):
    """One sentence for the run brief: the meeting, when it needs THIS agent, then the swarm's numbers."""
    note = ""
    try:
        m = open_meeting(http)
        if m:
            cs = _comments(m["number"], http)
            spoke = {(c.get("user") or {}).get("login") for c in cs}
            if ME == LEAD and _age_s(m) >= INPUT_WINDOW_S:
                note = (f"COMMITTEE MEETING #{m['number']}: {len(spoke - {LEAD})} of 12 members have spoken and the input "
                        "window has closed. Chair it NOW: `swarm-forge meeting`, then `swarm-forge meeting-minutes "
                        "\"## Decisions ... ## Commitments ...\"` - that closes it. ")
            elif ME not in spoke:
                note = (f"COMMITTEE MEETING #{m['number']} IS OPEN and has not heard from you. Read it (`swarm-forge "
                        "meeting`) and give your input this run: `swarm-forge meeting-input \"what worked / what "
                        "blocked / Proposal: ... / Commitment: ...\"`. ")
    except Exception:
        note = ""
    # What the OWNER reported outranks everything the swarm thought of itself. Issue #1 (anyone can accept an
    # answer) sat untouched for two hours with "fix first" written in the lead's rules: a rule in a long file
    # is not a line in the brief, and only the brief is read at the start of every run.
    try:
        s, mine = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=from-owner&limit=20")
        owed = [i for i in (mine if isinstance(mine, list) else [])
                if any((l or {}).get("name") == "from-owner" for l in (i.get("labels") or []))
                and any((a or {}).get("login") == ME for a in (i.get("assignees") or []))]
        if owed:
            note = (f"THE OWNER REPORTED #{owed[0]['number']} \"{owed[0]['title'][:70]}\" and it is still open and yours. "
                    "It comes before your own plan this run: fix it, test it, and answer on the issue with the commit. ") + note
    except Exception:
        pass
    try:
        swarm = subprocess.run(["vend-bridge", "swarm"], capture_output=True, text=True, timeout=20).stdout.splitlines()
        swarm = swarm[0] if swarm else ""
    except Exception:
        swarm = ""
    return (note + swarm).strip()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="swarm-forge", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="end-of-run comment on your territory issue"); r.add_argument("text")
    i = sub.add_parser("issue", help="ask the lead or another member for something")
    i.add_argument("title"); i.add_argument("body"); i.add_argument("--to", default="")
    c = sub.add_parser("comment"); c.add_argument("number"); c.add_argument("body")
    p = sub.add_parser("pr", help="push your branch and open a pull request into main"); p.add_argument("title"); p.add_argument("body")
    sub.add_parser("tasks", help="open issues assigned to you")
    sub.add_parser("inbox", help="open issues that mention you")
    sub.add_parser("meeting", help="the open committee meeting: agenda and what everyone has said")
    mi = sub.add_parser("meeting-input", help="your input (what worked, what blocked, Proposal:, Commitment:) or one reply")
    mi.add_argument("text")
    mm = sub.add_parser("meeting-minutes", help="LEAD: conclude with ## Decisions and ## Commitments; closes the meeting")
    mm.add_argument("text")
    sub.add_parser("brief-line", help="one sentence for the run brief")
    sub.add_parser("whoami")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "report": out = report(a.text)
        elif a.cmd == "issue": out = issue(a.title, a.body, a.to)
        elif a.cmd == "comment": out = comment(a.number, a.body)
        elif a.cmd == "pr": out = pr(a.title, a.body)
        elif a.cmd in ("tasks", "inbox"): out = listing(a.cmd)
        elif a.cmd == "meeting": out = meeting()
        elif a.cmd == "meeting-input": out = meeting_input(a.text)
        elif a.cmd == "meeting-minutes": out = meeting_minutes(a.text)
        elif a.cmd == "brief-line":
            print(brief_line())
            return 0
        else: out = {"member": ME, "repo": REPO, "forge": "https://swarm.vend-agent.xyz"}
    except Refused as ex:
        print(f"refused: {ex}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
