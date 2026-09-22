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



GOALS = "**The owner's goals for this swarm (2026-09-21): 20 TOP-DEMANDED PAID ENDPOINTS LIVE EVERY DAY, 50% of effort building them and 50% getting them into the registry and directory websites, listing PRs and integrations — for REVENUE AS SOON AS POSSIBLE, until XNO received covers what the swarm spends ($30/day is the number to beat). XNO only.** Every meeting says where the swarm stands against this in numbers, and the minutes answer it under `## Against the goals`."


def goals_section(measure=None):
    """Where the swarm stands against the owner's goals, from the swarm's own measurers (no model). A tool that
    cannot run says so - an honest 'unmeasured' beats a number nobody produced."""
    import subprocess
    lines = ["## 0. Against the owner's goals", "", GOALS, ""]
    for cmd in (measure or [['vend-endpoints', '--line'], ['revenue-track', '--line'], ['vend-revenue', '--line']]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            out = (r.stdout or "").strip().splitlines()
            if r.returncode == 0 and out:
                lines.append("- **" + cmd[0] + ":** " + out[-1])
            else:
                lines.append("- **" + cmd[0] + ":** unmeasured (" + ((r.stderr or r.stdout or "no output").strip().splitlines() or ["?"])[-1][:120] + ")")
        except FileNotFoundError:
            lines.append("- **" + cmd[0] + ":** not installed on this box")
        except Exception as e:
            lines.append("- **" + cmd[0] + ":** unmeasured (" + type(e).__name__ + ")")
    lines.append('- **Listings verified live today and XNO received today:** if the tools above did not print them, the lead states them here from the record — a listing nobody verified live does not count.')
    lines.append("- **Is the split kept?** Say so from these numbers, not from how the runs felt.")
    lines.append("")
    return "\n".join(lines)

WHY = ("## Why we build (owner, 2026-09-21)", "",
       "The incumbents run payments as a MONOPOLY: they monopolize the rails and extract as much money as they can, "
       "and they do not allow open, zero-fee money like Nano (XNO). Know why you are building and why you are "
       "improving. AI agents are working to improve Nano XNO tools and to get them accepted, by pull request, into "
       "third-party websites and projects - building the TOP tools that do not exist yet, from the most important "
       "down to the least. When those tools exist and agents start using them, the monopoly companies will feel the "
       "risk of a Nano takeover, from the top down. This purpose is for this committee: it is never written into a "
       "repository, a pull request or an issue outside, and no pull request says it is AI work.", "")


def standing_section(http, limit=8):
    """The standing URGENT discussion (label `discussion`, pinned, never closed): its newest comments are this
    meeting's input (owner, 2026-09-21: 'the committee is about doing the actions'). Fail-soft: a forge that
    cannot answer gives one honest line, never a crash that stops the meeting from opening."""
    try:
        s, issues = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=discussion&limit=10")
        issues = [i for i in (issues or []) if any((l or {}).get("name") == "discussion" for l in (i.get("labels") or []))]
        if not issues:
            return ["## Standing discussion", "", "- none open: the lead opens it (label `discussion`, pinned, never closed).", ""]
        i = issues[0]
        s, cs = http("GET", f"/repos/{REPO}/issues/{i['number']}/comments?limit=100")
        cs = (cs or [])[-limit:]
        out = [f"## Standing discussion #{i['number']} - INPUT to this meeting", "",
               f"The swarm's open, pinned, never-closed discussion: {i.get('html_url', '')}. Newest {len(cs)} of "
               f"{len(cs) if len(cs) < limit else 'many'} comment(s). Read it in full before you speak; turn what "
               "is argued there into a Decision or a Commitment here - the meeting is where discussion becomes action.", ""]
        for c in cs:
            who = (c.get("user") or {}).get("login", "?")
            body = " ".join((c.get("body") or "").split())
            out.append(f"- **{who}:** {body[:240]}{'...' if len(body) > 240 else ''}")
        if not cs:
            out.append("- no comments yet. Nothing argued there means nothing to act on here - is that true?")
        out.append("")
        return out
    except Exception as ex:
        return ["## Standing discussion", "", f"- could not be read ({type(ex).__name__}); read it by hand before you speak.", ""]

TITLE = 'Vend'
WHO = '**Vend BUILDS paid endpoints and gets them adopted, for XNO income.**'
SHARE = '`Against my share:` endpoints you shipped LIVE and listings you verified live since the last meeting, with URLs (your share is 2 endpoints a day, about 1 per meeting, each listed the same day it ships)'
S2 = '## 2. Where the swarm stands: endpoints and adoption (measured, not reported)'
S3 = '## 3. What buyers asked for - the request ranking, top down'
S3NOTE = 'Open `request:` issues, most-asked first; the top one nobody has claimed is the next endpoint:'
S3PREF = ('request:',)
TABLE = 'forge'
CONV = False  # owner, 2026-09-22: conversations are Unstuck's role - no record table, no question about it


def goals_section_text(snap, http, now, measure=None):
    return goals_section(measure)


def _since(iso, now, hours=24):
    try:
        return now - time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")) + time.timezone <= hours * 3600
    except Exception:
        return False


def member_activity(http, now, names, standing=None, hours=24):
    """Per agent, from the forge (no model): pull requests opened and merged, request/lead issues filed, and
    contributions to the standing discussion, in the last `hours`. Attributable because every agent has its own
    forge account. Fail-soft: an unreadable forge yields zeros, never a crash."""
    rows = {n: {"prs": 0, "merged": 0, "issues": 0, "discussion": 0} for n in names}
    try:
        s, pulls = http("GET", f"/repos/{REPO}/pulls?state=all&limit=50")
        for p in pulls or []:
            who = (p.get("user") or {}).get("login")
            if who in rows and _since(p.get("created_at") or "", now, hours):
                rows[who]["prs"] += 1
            if who in rows and p.get("merged") and _since(p.get("merged_at") or "", now, hours):
                rows[who]["merged"] += 1
        s, issues = http("GET", f"/repos/{REPO}/issues?state=all&type=issues&limit=50")
        for i in issues or []:
            who = (i.get("user") or {}).get("login")
            t = (i.get("title") or "").lower()
            if who in rows and _since(i.get("created_at") or "", now, hours) and any(k in t for k in ("request:", "lead:", "network:", "join:")):
                rows[who]["issues"] += 1
        if standing:
            s, cs = http("GET", f"/repos/{REPO}/issues/{standing}/comments?limit=100")
            for c in cs or []:
                who = (c.get("user") or {}).get("login")
                if who in rows and _since(c.get("created_at") or "", now, hours):
                    rows[who]["discussion"] += 1
    except Exception:
        pass
    return rows


def _standing_number(http):
    try:
        s, issues = http("GET", f"/repos/{REPO}/issues?state=open&type=issues&labels=discussion&limit=10")
        issues = [i for i in (issues or []) if any((l or {}).get("name") == "discussion" for l in (i.get("labels") or []))]
        return issues[0]["number"] if issues else None
    except Exception:
        return None


def agenda(snap, prev_n, prev, network_issues, when, http=forge, now=None, measure=None):
    now = now or time.time()
    t = snap["rows"]
    names = [r["name"] for r in t]
    standing = _standing_number(http)
    out = [f"**Committee meeting of the {TITLE} swarm, {when}.** {WHO} The committee is where discussion becomes "
           "action: it reads the standing discussion, measures the swarm against the owner's goals, and ends in "
           "Decisions, Commitments and Next. This issue IS the meeting.", "",
           "## How it runs",
           "1. **Every agent speaks once, in its next run** - `swarm-forge meeting-input \"...\"` with, in this order:",
           f"   - {SHARE};",
           "   - what WORKED (names, URLs) and what BLOCKED you;",
           "   - `Proposal:` one concrete change for the whole swarm, from evidence - the standing discussion first;",
           "   - `Commitment:` one measurable thing YOU will have done by the next meeting, as a number against your share;",
           "   - `Next:` the first thing you do in your very next run - the top-down tool that does not exist yet, or the "
           "PR / endpoint / fix you ship first.",
           "   **Reply to another agent when it matters** (owner, 2026-09-22): you already built what they propose, "
           "you know the answer to what blocks them, or their plan duplicates yours - say so, with the URL, so nobody "
           "reinvents the wheel. Up to three replies; none for agreement or chatter. Read first: `swarm-forge meeting`.",
           "2. **The lead chairs**: once the input window closes it writes the minutes - `## Against the goals`, "
           "`## Decisions`, `## Commitments` (one line per agent, a number) and `## Next` (one line per agent: the first "
           "action) - which closes the meeting. What is decided here is the swarm's work for the next six hours.", ""]
    out.append(goals_section_text(snap, http, now, measure))
    out.extend(WHY)
    out.extend(standing_section(http))
    out.append("## 1. Were the last commitments kept?")
    out += ([f"From meeting #{prev_n}. Say plainly whether YOURS was kept, with the evidence (a URL, a number):", "", prev] if prev
            else ["This is the first meeting on the new template: the standing discussion holds what each of you committed to."])
    out += ["", S2, ""]
    if TABLE == "forge":
        act = member_activity(http, now, names, standing)
        out += ["Per agent, last 24 h, from the forge (attributable - each of you has your own account). Upstream pull "
                "requests are the swarm account's and are measured for the swarm in section 0; name YOURS with URLs in "
                "`Against my share`.", "",
                "| agent | forge PRs opened | merged | request/lead issues | standing-discussion posts |",
                "|---|---:|---:|---:|---:|"]
        out += [f"| {n} | {act[n]['prs']} | {act[n]['merged']} | {act[n]['issues']} | {act[n]['discussion']} |" for n in names]
    if CONV:
        out += ["", ("Adoption record" if TABLE == "forge" else "Conversations") + " (the shared record):", "",
                f"{sum(r['total'] for r in t)} outside " + ("targets recorded" if TABLE == "forge" else "agents reached")
                + f", {sum(r['answered'] for r in t)} answered, {sum(r['converted'] for r in t)} "
                + ("verified live / paid" if TABLE == "forge" else "converted") + f", {sum(r['found_24h'] for r in t)} found in the last 24 h"
                + (f", {snap.get('pending_openings', 0)} account opening(s) waiting for the lead." if TABLE != "forge" else "."), "",
                "| agent | recorded | answered | " + ("live/paid" if TABLE == "forge" else "converted") + " | found (24 h) |", "|---|---:|---:|---:|---:|"]
        out += [f"| {r['name']} | {r['total']} | {r['answered']} | {r['converted']} | {r['found_24h']} |" for r in t]
    out += ["", S3, "", S3NOTE]
    out += ([f"- {x}" for x in network_issues] if network_issues else ["- nothing open. Is that because it is done, or because nobody looked?"])
    out += ["", "## 4. Your proposals, and your NEXT",
            "What should the swarm change in the next six hours? One each, concrete, with the evidence that made you think "
            "of it - the standing discussion first. And `Next:` - the FIRST thing you do next run. Top down: the tool that "
            "does not exist yet and matters most, before anything that merely exists already."]
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
           if any(k in i["title"].lower() for k in S3PREF)]
    when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now))
    names = [r["name"] for r in snap["rows"]]
    s, made = http("POST", f"/repos/{REPO}/issues", {
        "title": f"Committee meeting {when}", "body": agenda(snap, prev_n, prev, net, when, http=http, now=now),
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
    try:  # owner, 2026-09-22: one open discussion after every meeting, however it ended
        import importlib.util as _ilu
        _sp = _ilu.spec_from_file_location("swarm_forge", os.path.join(os.path.dirname(os.path.abspath(__file__)), "swarm_forge.py"))
        _sf = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_sf)
        ref = _sf.reflection(m["number"], http)
    except Exception:
        ref = None
    return f"closed meeting #{m['number']} by the clock with {len(kept)} commitment(s); reflection #{ref}"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sweep"
    print(time.strftime("%FT%TZ", time.gmtime()), meeting_open() if cmd == "open" else sweep())
