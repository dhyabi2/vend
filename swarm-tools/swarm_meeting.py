#!/usr/bin/env python3
"""The swarm's committee meeting, every six hours (owner, 2026-09-20).

Thirteen agents never run at the same moment, so the meeting is an ISSUE with the label `meeting`, not a call:
  * `open` (cron, on the six-hour mark) opens it with an agenda made of MEASUREMENTS: each agent's numbers, the
    open network bugs, and the commitments the last meeting ended with - so item one is whether they were kept;
  * every agent finds it at the top of its next run brief and speaks (`swarm-forge meeting-input`);
  * after the input window the lead's brief tells it to chair: minutes with `## Decisions` and
    `## Commitments`, which closes the issue (`swarm-forge meeting-minutes`);
  * `sweep` (cron) closes a meeting the lead never concluded after five hours, keeping the commitments the
    members wrote themselves, so meetings never pile up and the next can always open.
Nothing here asks a model anything.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vend_swarm as S  # noqa: E402

API = "http://127.0.0.1:3000/api/v1"
REPO = "swarm/vend"
AUTOCLOSE_S = 5 * 3600


def forge(method, path, payload=None):
    token = open("/root/.vend-swarm/vend.token", encoding="utf-8").read().strip()
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={"Authorization": "token " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as ex:
        return ex.code, None


def label_id(http=forge):
    s, labels = http("GET", f"/repos/{REPO}/labels?limit=50")
    for l in labels or []:
        if l["name"] == "meeting":
            return l["id"]
    s, l = http("POST", f"/repos/{REPO}/labels", {"name": "meeting", "color": "#fbca04",
                                                  "description": "Committee meeting: inputs, minutes, commitments"})
    return l["id"]


def last_commitments(http=forge):
    """(number, the Commitments section verbatim) of the most recent concluded meeting."""
    s, closed = http("GET", f"/repos/{REPO}/issues?state=closed&type=issues&labels=meeting&limit=20")
    closed = only_meetings(closed)
    if not closed:
        return None, ""
    n = closed[0]["number"]
    s, cs = http("GET", f"/repos/{REPO}/issues/{n}/comments?limit=100")
    for c in reversed(cs or []):
        body = c.get("body", "")
        i = body.lower().find("## commitments")
        if i >= 0:
            return n, body[i:i + 2500].strip()
    return n, ""


def only_meetings(issues):
    """The forge ignores a label it does not know and returns everything: trust the issue, not the query."""
    return [i for i in (issues or []) if any((l or {}).get("name") == "meeting" for l in (i.get("labels") or []))]


def agenda(snap, prev_n, prev, network_issues, when):
    t = snap["rows"]
    out = [f"**Committee meeting of the Vend swarm, {when}.** One purpose: make the swarm better at its "
           "mission, from what each of you actually saw. This issue IS the meeting.", "",
           "## How it runs",
           "1. **Every agent speaks once, in its next run**: `swarm-forge meeting-input \"...\"` with what WORKED "
           "(names, URLs), what BLOCKED you, a line `Proposal:` - one concrete change that would make the whole "
           "swarm better - and a line `Commitment:` - one measurable thing you will have done by the next "
           "meeting. You may reply ONCE to someone else's proposal. Read first: `swarm-forge meeting`.",
           "2. **The lead chairs**: once the input window closes it writes the minutes - `## Decisions` and "
           "`## Commitments`, one line per agent - which closes the meeting.", ""]
    out.append("## 1. Were the last commitments kept?")
    out += ([f"From meeting #{prev_n}. Say plainly whether YOURS was kept, with the evidence:", "", prev] if prev
            else ["This is the first meeting: there are none yet. After today there always will be."])
    out += ["", "## 2. Where the swarm stands (measured, not reported)", "",
            f"{sum(r['total'] for r in t)} outside agents reached, {sum(r['answered'] for r in t)} answered, "
            f"{sum(r['converted'] for r in t)} converted, {sum(r['found_24h'] for r in t)} found in the last 24 h, "
            f"{snap['pending_openings']} account opening(s) waiting for the lead.", "",
            "| agent | conversations | answered | converted | found (24 h) |", "|---|---:|---:|---:|---:|"]
    out += [f"| {r['name']} | {r['total']} | {r['answered']} | {r['converted']} | {r['found_24h']} |" for r in t]
    out += ["", "## 3. The network: what is broken or hard to join"]
    out += ([f"- {x}" for x in network_issues] if network_issues else ["- nothing open. Is that because it works, or because nobody tried it as a newcomer?"])
    out += ["", "## 4. Your proposals", "What should the swarm change in the next six hours? One each, concrete, "
            "with the evidence that made you think of it."]
    return "\n".join(out)


def meeting_open(now=None, http=forge, snapshot=None):
    now = now or time.time()
    label_id(http)                       # make sure the label exists before anything filters on it
    s, already = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=meeting&limit=20")
    already = only_meetings(already)
    if already:
        return f"meeting #{already[0]['number']} is still open; not opening a second"
    snap = (snapshot or S.snapshot)(now)
    prev_n, prev = last_commitments(http)
    s, issues = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&limit=50")
    net = [f"#{i['number']} {i['title']}" for i in (issues or [])
           if "network:" in i["title"].lower() or "join:" in i["title"].lower()]
    when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now))
    names = [r["name"] for r in snap["rows"]]
    s, made = http("POST", f"/repos/{REPO}/issues", {
        "title": f"Committee meeting {when}", "body": agenda(snap, prev_n, prev, net, when),
        "labels": [label_id(http)], "assignees": names})
    return f"opened meeting #{made['number']}" if s == 201 and made else f"could not open the meeting ({s})"


def sweep(now=None, http=forge):
    """Close a meeting nobody concluded, keeping what the members committed to in their own words."""
    import calendar
    now = now or time.time()
    s, open_ = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=meeting&limit=20")
    open_ = only_meetings(open_)
    if not open_:
        return "no meeting open"
    m = open_[0]
    age = now - calendar.timegm(time.strptime(m["created_at"][:19], "%Y-%m-%dT%H:%M:%S"))
    if age < AUTOCLOSE_S:
        return f"meeting #{m['number']} is {round(age / 3600, 1)} h old; the lead has until {AUTOCLOSE_S // 3600} h"
    s, cs = http("GET", f"/repos/{REPO}/issues/{m['number']}/comments?limit=100")
    kept = []
    for c in cs or []:
        who = (c.get("user") or {}).get("login", "?")
        for line in c.get("body", "").splitlines():
            if line.strip().lower().startswith("commitment:"):
                kept.append(f"- {who}: {line.split(':', 1)[1].strip()}")
    body = ("# Minutes of meeting (closed by the clock)\n\nThe lead did not conclude this meeting within "
            f"{AUTOCLOSE_S // 3600} hours, so no decisions were taken. That is itself the first item for the next one.\n\n"
            "## Decisions\n- none\n\n## Commitments\n" + ("\n".join(kept) if kept else "- none were made"))
    http("POST", f"/repos/{REPO}/issues/{m['number']}/comments", {"body": body})
    http("PATCH", f"/repos/{REPO}/issues/{m['number']}", {"state": "closed"})
    return f"closed meeting #{m['number']} by the clock with {len(kept)} commitment(s)"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sweep"
    print(time.strftime("%FT%TZ", time.gmtime()), meeting_open() if cmd == "open" else sweep())
