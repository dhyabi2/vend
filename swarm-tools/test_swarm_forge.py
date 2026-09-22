#!/usr/bin/env python3
"""Laws for swarm-forge. The forge is PUBLIC (owner, 2026-09-20), so the first law is that a secret never posts."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["RAI_SWARM_MEMBER"] = "atlas"
os.environ["SWARM_FORGE_TOKEN_FILE"] = os.path.join(tempfile.mkdtemp(), "none")
import swarm_forge as F


class Forge:
    def __init__(self): self.posts = []
    def __call__(self, method, path, body=None, api=None):
        if method == "GET" and "/labels" in path:
            return 200, [{"id": 1, "name": "network-bug"}, {"id": 2, "name": "join"}, {"id": 3, "name": "lead"},
                         {"id": 4, "name": "request"}, {"id": 5, "name": "agent:atlas"}, {"id": 6, "name": "from-swarm"}]
        if method == "GET":
            return 200, [{"number": 3, "title": "Territory: beacon", "assignees": [{"login": "beacon"}]},
                         {"number": 2, "title": "Territory: atlas", "assignees": [{"login": "atlas"}]}]
        self.posts.append((path, body)); return 201, {"number": 9, "html_url": "https://swarm.vend-agent.xyz/x"}


def refused(fn, needle):
    try: fn()
    except F.Refused as ex:
        assert needle in str(ex), (needle, str(ex)); return
    raise AssertionError("not refused: " + needle)


def test():
    f = Forge()
    good = "Found 6 A2A agents on the a2a registry; orbit.example.com answered asking how custody works. Blocked: none."
    out = F.report(good, http=f)
    assert out["reported_on"] == 2 and f.posts[-1][0].endswith("/issues/2/comments"), "a report goes on YOUR territory issue"
    refused(lambda: F.report("all good", http=f), "says nothing")
    n = len(f.posts)
    for leak in ("the key is sk-nano-00000000-aaaa-bbbb-cccc-dddddddddddd",
                 "token github_pat_00FAKEFAKEFAKEFAKEFAKE_notARealTokenAtAll00",
                 "seed " + "A1" * 32,
                 "curl -H 'Authorization: token 0123456789abcdef0123456789abcdef01234567'"):
        refused(lambda: F.report(good + " " + leak, http=f), "looks like a secret")
        refused(lambda: F.issue("Need a crawler for agent cards", leak, http=f), "looks like a secret")
    assert len(f.posts) == n, "a refused text must never reach the forge"
    # A block hash is 64 hex as well, and is exactly the evidence a report should carry.
    F.report(good + " Starter sent, block " + "AB" * 32, http=f)
    F.issue("Need a crawler for agent cards", "The a2a registry paginates; a shared crawler would help every member.", http=f)
    assert f.posts[-1][1]["title"].startswith("[atlas] "), "every issue says who opened it"
    # The owner saw issues arriving with no labels: the prefix the rules ask for must BECOME the label.
    assert f.posts[-1][1]["labels"] == [4, 5], "no prefix: a request, and the agent that opened it"
    out = F.issue("network: accept works for anyone who names the asker", "POST /ask/1/accept with acceptedBy set to the asker succeeds from any caller; expected a refusal.", http=f)
    assert f.posts[-1][1]["labels"] == [1, 5] and f.posts[-1][1]["assignees"] == ["vend"], "a network bug is labelled and goes to the lead"
    assert out["labels"] == ["network-bug", "agent:atlas"]
    F.issue("join: agents without a wallet cannot complete step 2", "Three agents stopped at the address field: they have no wallet yet and the form requires one.", http=f)
    assert f.posts[-1][1]["labels"] == [2, 5]
    F.issue("lead: Yabibal builds LangGraph agent frameworks", "Found via aegis-agent; outside my territory, flint holds frameworks.", to="flint", http=f)
    assert f.posts[-1][1]["labels"] == [3, 5] and f.posts[-1][1]["assignees"] == ["flint"]
    print("PASS swarm-forge: a report lands on the member's own territory issue, a thin one is refused, anything "
          "shaped like a key, a token or a seed posts nothing while a block hash may, and every issue names its author")


class Meeting:
    """A forge with one open meeting."""
    def __init__(self, age_s=600):
        import time
        self.comments, self.closed, self.posts = [], False, []
        self.created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - age_s))
    def __call__(self, method, path, body=None, api=None):
        if method == "GET" and "labels=meeting" in path:
            # Like the real forge: an unknown label filters nothing, so other issues come back too.
            other = {"number": 13, "title": "Territory: lumen", "labels": [{"name": "territory"}], "created_at": self.created}
            return 200, [other] + ([] if self.closed else [{"number": 20, "title": "Committee meeting", "body": "agenda",
                                                           "labels": [{"name": "meeting"}], "created_at": self.created}])
        if method == "GET":
            return 200, list(self.comments)
        if method == "PATCH":
            self.closed = body.get("state") == "closed"; return 201, {}
        self.comments.append({"user": {"login": F.ME}, "body": body["body"]}); self.posts.append(body["body"])
        return 201, {"html_url": "https://swarm.vend-agent.xyz/x"}


def test_meeting():
    m = Meeting()
    F.ME = "atlas"
    assert "COMMITTEE MEETING #20 IS OPEN and has not heard from you" in F.brief_line(http=m)
    refused(lambda: F.meeting_input("things are going fine", http=m), "Against my share")
    good = ("Against my share: 2 of 2, https://x/1 https://x/2. Worked: the a2a registry crawl found 9 agents, orbit.example.com answered within the hour. Blocked: half the "
            "agent cards list an endpoint that 404s. Proposal: a shared agent-card validator every member can call before "
            "claiming. Commitment: 10 validated A2A agents claimed and 3 conversations past `replied` by the next meeting. Next: open the accept-XNO drop-in PR on x/y first, then the validator.")
    assert F.meeting_input(good, http=m)["spoken"] == 1
    assert "COMMITTEE" not in F.brief_line(http=m), "once you have spoken the brief stops asking"
    refused(lambda: F.meeting_input("agree", http=m), "adds nothing")
    F.meeting_input("To beacon's proposal on MCP registries: the validator should also check the card's auth scheme, "
                    "because three of mine needed an API key nobody can get.", http=m)
    # Owner, 2026-09-22: replies are for when they change what another agent will do - up to three, then it is a chat.
    F.meeting_input("Second reply: I already built that validator last week, it is at https://x/validator - reuse it, do not rebuild.", http=m)
    F.meeting_input("Third reply: your plan duplicates mine on MCP registries; I hold that ground, take the A2A half.", http=m)
    refused(lambda: F.meeting_input(good, http=m), "A meeting is not a chat")
    refused(lambda: F.meeting_minutes("## Decisions\n...\n## Commitments\n...", http=m), "the lead chairs")

    F.ME = "vend"
    assert "COMMITTEE" in F.brief_line(http=Meeting(age_s=600)), "the lead is a member too: it gives input first"
    late = Meeting(age_s=F.INPUT_WINDOW_S + 60); late.comments = [{"user": {"login": "atlas"}, "body": good}, {"user": {"login": "vend"}, "body": good}]
    assert "Chair it NOW" in F.brief_line(http=late) and "1 of 12 members" in F.brief_line(http=late)
    early = Meeting(age_s=3900); early.comments = [{"user": {"login": n}, "body": good} for n in ("beacon", "kite", "delta")]
    refused(lambda: F.meeting_minutes("## Decisions\n" + "x" * 300 + "\n## Commitments\n- a: b", http=early), "only 3 of 12 members have spoken")
    refused(lambda: F.meeting_minutes("we talked", http=late), "## Decisions")
    # Owner, 2026-09-21: minutes must show where the swarm stands against the owner's goals.
    refused(lambda: F.meeting_minutes("## Decisions\n" + "x" * 300 + "\n## Commitments\n- a: b", http=late), "## Next")
    refused(lambda: F.meeting_minutes("## Decisions\n" + "x" * 300 + "\n## Commitments\n- a: b\n## Next\n- a: b", http=late), "## Against the goals")
    minutes = ("## Against the goals\n- section 0 numbers restated; the split was kept these six hours.\n\n## Decisions\n- Build the shared agent-card validator atlas proposed: 'half the agent cards list an endpoint that "
               "404s' costs every member the same wasted claims.\n- Territory for MCP registries stays with beacon.\n\n"
               "## Commitments\n- atlas: 10 validated A2A agents claimed, 3 conversations past replied\n- vend: issue #1 fixed "
               "and deployed, validator merged\n\n## Next\n- member: the validator PR first\n- lead: merge and deploy it\n")
    out = F.meeting_minutes(minutes, http=late)
    assert out["closed"] and late.closed and late.posts[-1].startswith("# Minutes of meeting")
    assert F.open_meeting(http=late) is None, "an issue without the meeting label is never a meeting"
    class Owed(Meeting):
        def __call__(self, method, path, body=None, api=None):
            if method == "GET" and "labels=from-owner" in path:
                return 200, [{"number": 1, "title": "network: anyone can accept an answer by naming the asker",
                              "labels": [{"name": "from-owner"}], "assignees": [{"login": "vend"}]},
                             {"number": 13, "title": "Territory: lumen", "labels": [{"name": "territory"}], "assignees": [{"login": "vend"}]}]
            return super().__call__(method, path, body, api)
    F.ME = "vend"
    line = F.brief_line(http=Owed())
    assert line.startswith("THE OWNER REPORTED #1") and "#13" not in line, line
    F.ME = "atlas"
    assert "THE OWNER REPORTED" not in F.brief_line(http=Owed()), "only the agent it is assigned to is told"
    print("PASS committee: an open meeting is put in front of every agent that has not spoken, an input needs what "
          "worked, what blocked, a Proposal and a Commitment, each agent speaks at most four times (an input and three replies that change what another agent will do), only the lead concludes "
          "and only with Decisions and Commitments, and concluding closes the issue")


def test_a_broken_forge_tool_is_never_silent():
    """Two leads had no token where the tool looks; every call was refused and the brief looked normal for three hours."""
    def refused(method, path, body=None):
        raise F.Refused("no forge token at /root/.hermes/forge.token")
    line = F.brief_line(http=refused)
    assert "YOUR FORGE TOOL IS NOT WORKING" in line and "no forge token" in line, line
    def flaky(method, path, body=None):
        raise TimeoutError("the forge did not answer")
    assert "NOT WORKING" not in F.brief_line(http=flaky), "one slow answer is not a broken tool"
    print("PASS forge tool: a refusal to authenticate is the first thing in the brief, a single timeout is not")


def test_lead_brief_puts_the_merge_queue_first():
    """Owner, 2026-09-22 ("why the number of endpoints not increased"): 13 PRs sat open 20 h while the only merger
    never looked. A queue older than two hours is the FIRST line of the lead's brief, naming each PR and its state."""
    import time as _t
    old_ts = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(_t.time() - 5 * 3600))
    new_ts = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(_t.time() - 600))
    prs = [{"number": 100, "created_at": old_ts, "mergeable": False, "user": {"login": "flux"}},
           {"number": 107, "created_at": old_ts, "mergeable": True, "user": {"login": "lathe"}},
           {"number": 120, "created_at": new_ts, "mergeable": False, "user": {"login": "dynamo"}}]
    def http(method, path, body=None):
        if "/pulls" in path:
            return 200, prs
        return 200, []
    line = F.merge_queue_line(http=http)
    assert line.startswith("MERGE QUEUE FIRST: 3 pull requests"), line
    assert "#107 lathe 5h" in line and "Mergeable now" in line, line
    assert "#100 flux 5h" in line and "#120 dynamo 0h" in line and "rebase" in line, line
    young = [dict(p, created_at=new_ts) for p in prs]
    assert F.merge_queue_line(http=lambda m, p, b=None: (200, young if "/pulls" in p else [])) == "", "a young queue is not an alarm"
    assert F.merge_queue_line(http=lambda m, p, b=None: (200, [])) == ""
    def broken(method, path, body=None):
        raise TimeoutError("forge slow")
    assert F.merge_queue_line(http=broken) == "", "an unreadable forge is not a false alarm"
    old_me = F.ME
    try:
        F.ME = F.LEAD
        assert F.brief_line(http=http).startswith("MERGE QUEUE FIRST"), "the lead's brief opens with the queue"
        F.ME = "flux"
        assert "MERGE QUEUE" not in F.brief_line(http=http), "a member does not merge; its brief says nothing about the queue"
    finally:
        F.ME = old_me
    print("PASS merge queue: a PR older than two hours puts the whole queue first in the LEAD's brief, mergeable and "
          "conflicted named with author and age; a young or empty queue, a member's brief and an unreadable forge say nothing")


def test_every_meeting_is_followed_by_a_pinned_open_discussion():
    """Owner, 2026-09-22: after each meeting's minutes, one open-discussion issue - no template, non-technical, the
    monopoly / what you think / your focus, POSITIVE only - pinned, every agent assigned and asked to comment; the
    previous one is unpinned but stays open; a forge failure never undoes the minutes."""
    calls = []
    members = ["m%d" % i for i in range(12)]
    def http(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET" and "labels=territory" in path:
            return 200, [{"number": 10 + i, "labels": [{"name": "territory"}], "assignees": [{"login": m}]} for i, m in enumerate(members)]
        if method == "GET" and path.endswith("/labels?limit=100"):
            return 200, [{"id": 9, "name": "reflection"}]
        if method == "GET" and "labels=reflection" in path:
            return 200, [{"number": 40, "labels": [{"name": "reflection"}], "pin_order": 1}]
        if method == "POST" and path.endswith("/issues"):
            return 201, {"number": 77}
        return 200, {}
    n = F.reflection(41, http=http)
    assert n == 77, n
    made = next(b for m, p, b in calls if m == "POST" and p.endswith("/issues"))
    assert set(made["assignees"]) == set(members) | {F.LEAD}, made["assignees"]
    assert made["labels"] == [9] and "after meeting #41" in made["title"], made
    body = made["body"]
    for want in ("monopoly", "What you are thinking", "focus", "negativity is not allowed", "No template", "nothing technical"):
        assert want in body, want
    assert all("@" + m in body for m in members) and "leave your comment" in body
    assert ("DELETE", f"/repos/{F.REPO}/issues/40/pin", None) in calls, "the previous discussion is unpinned"
    assert ("POST", f"/repos/{F.REPO}/issues/77/pin", None) in calls, "the new one is pinned"
    assert not any(m == "PATCH" for m, p, b in calls), "nothing is closed"
    def broken(method, path, body=None):
        raise TimeoutError("forge down")
    assert F.reflection(41, http=broken) is None, "never raises"
    print("PASS reflection: a pinned open discussion follows every meeting, every agent assigned and asked, positive "
          "only, the previous one unpinned but open, and a broken forge never undoes the minutes")


def test_the_open_discussion_is_in_the_brief_until_the_agent_has_spoken():
    """Owner noticed (2026-09-22): eleven of twelve members ran and left no comment - the brief never named it."""
    def http(method, path, body=None):
        if "labels=reflection" in path:
            return 200, [{"number": 84, "labels": [{"name": "reflection"}]}]
        if path.endswith("/issues/84/comments?limit=100") or "/issues/84/comments" in path:
            return 200, [{"user": {"login": "kelp"}}]
        return 200, []
    old = F.ME
    try:
        F.ME = "aster"
        line = F.reflection_line(http=http)
        assert line.startswith("OPEN DISCUSSION #84") and "swarm-forge comment 84" in line and "positive" in line, line
        assert "OPEN DISCUSSION #84" in F.brief_line(http=http)
        F.ME = "kelp"
        assert F.reflection_line(http=http) == "", "an agent that has spoken is not nagged"
    finally:
        F.ME = old
    def broken(method, path, body=None):
        raise TimeoutError("forge slow")
    assert F.reflection_line(http=broken) == ""
    print("PASS open discussion in the brief: named, with the command, until this agent has commented; silent on a broken forge")


if __name__ == "__main__":
    test_the_open_discussion_is_in_the_brief_until_the_agent_has_spoken()
    test_every_meeting_is_followed_by_a_pinned_open_discussion()
    test()
    test_meeting()
    test_a_broken_forge_tool_is_never_silent()
    test_lead_brief_puts_the_merge_queue_first()
