#!/usr/bin/env python3
"""Laws for swarm-forge. The forge is PUBLIC (owner, 2026-09-20), so the first law is that a secret never posts."""
import os, re, sys, tempfile
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
    early = Meeting(age_s=F.INPUT_WINDOW_S - 300)   # inside the window: meetings are half-hourly now
    early.comments = []
    early.comments; early.comments = [{"user": {"login": n}, "body": good} for n in ("beacon", "kite", "delta")]
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


def test_the_write_path_is_measured_in_every_brief():
    """Owner, 2026-09-22: a day after the classic token arrived agents still repeated 'the fine-grained PAT blocks
    every write' from their notes. The brief now carries GitHub's own answer, every run."""
    class Out:
        def __init__(self, s): self.stdout = s
    classic = Out("HTTP/2.0 200 OK\nX-Oauth-Scopes: admin:org, repo, workflow\n\n{\"login\": \"PANDeveloper001\"}")
    line = F.write_path_line(run=lambda: classic)
    assert line.startswith("GITHUB WRITE PATH: OPEN") and "drafts/" in line and "stale" in line, line
    fine = Out("HTTP/2.0 200 OK\nX-Github-Request-Id: x\n\n{\"login\": \"PANDeveloper001\"}")
    assert F.write_path_line(run=lambda: fine).startswith("GITHUB WRITE PATH: CLOSED - the token in `gh` is fine-grained")
    narrow = Out("HTTP/2.0 200 OK\nX-Oauth-Scopes: gist, read:org\n\n{}")
    assert "CLOSED" in F.write_path_line(run=lambda: narrow) and "without `repo`" in F.write_path_line(run=lambda: narrow)
    assert F.write_path_line(run=lambda: Out("")) == "", "no answer from GitHub says nothing"
    def boom():
        raise OSError("no gh")
    assert F.write_path_line(run=boom) == ""
    print("PASS write path measured: OPEN with a classic repo-scoped token (drafts are deliverables, the old note is called "
          "stale), CLOSED for a fine-grained or narrow token, silent when GitHub does not answer")



def test_announce_is_checked_before_the_issue_exists_and_the_brief_measures_x():
    """Owner, 2026-09-23 ("why X posting stopped again, agents also are not posting"). Five announces ever, two refused
    by the rail for rules the agent never saw. The tool refuses those shapes first, naming the rule; a good one passes;
    and the brief carries a measured X line with the order to announce this run's win."""
    for title, body, word in (
            ("announce: Vend's MCP discovery manifest is live - .well-known/mcp - so agent-MCP directories can index it", "https://extract.paypercall.dev/.well-known/mcp", "15 words"),
            ("announce: none this run", "https://example.org/x", "not an announcement"),
            ("announce: MCP discovery manifest live", "see https://github.com/PANDeveloper001/vend/pull/3", "never a repository we own"),
            ("announce: MCP discovery manifest live", "went live today", "needs ONE https link")):
        try:
            F.announce_check(title, body)
            raise AssertionError(("must be refused", title))
        except F.Refused as ex:
            assert word in str(ex), (word, str(ex))
    F.announce_check("announce: MCP discovery manifest live", "Vend's manifest: https://extract.paypercall.dev/.well-known/mcp")
    F.announce_check("network: something else entirely with many many words in its long title here", "no link needed")
    import time as _t  # noqa: WPS433
    today = _t.strftime("%Y-%m-%d", _t.gmtime())
    def http(method, path, payload=None):
        if "labels=x-posting" in path:
            return 200, [{"number": 75, "labels": [{"name": "x-posting"}]}]
        if "/issues/75/comments" in path:
            return 200, [{"created_at": today + "T00:40:00Z", "body": "**POSTED** https://x.com/i/web/status/1"},
                         {"created_at": today + "T00:25:00Z", "body": "**FAILED** - #156: 18 words"},
                         {"created_at": "2026-09-01T00:00:00Z", "body": "**POSTED** old"}]
        if "labels=announce" in path:
            return 200, [{"number": 99, "labels": [{"name": "announce"}]}]
        return 200, []
    line = F.announce_line(http)
    assert line.startswith("X TODAY: 1 posted from this swarm, 1 refused, 1 announce issue(s) waiting"), line
    assert "announce: <at most 10 words>" in line and "Nothing went live = open nothing" in line
    assert F.announce_line(lambda *a, **k: (_ for _ in ()).throw(OSError("down"))) == "", "an unreadable forge drops the line, never the brief"
    print("PASS announce: 18 words, 'none this run', an owned link and no link are refused before the issue exists; a 10-word "
          "headline with a stranger-checkable link passes; the brief's X line is measured (posted/refused/waiting) and orders "
          "the announce; an unreadable forge drops the line")


def test_throttled_account_is_measured_and_the_brief_orders_drafts_not_calls():
    """Owner, 2026-09-23 ("work like previously, 100 PRs per day"): after GitHub's security reset the account is flagged
    and throttled to anonymous limits (core 60/h, GraphQL 0). The brief measures it every run: throttled -> no GitHub
    call, build and keep PRs under drafts/; a normal limit -> the OPEN line as before; an unreadable limit -> OPEN
    (the scope header already proved the token), never a false THROTTLED."""
    import json as _j  # noqa: WPS433
    class Out:
        def __init__(self, stdout): self.stdout = stdout
    classic = Out("HTTP/2.0 200 OK\r\nX-Oauth-Scopes: repo, workflow\r\n\r\n{}")
    def run_with(limit, left, gl):
        body = _j.dumps({"resources": {"core": {"limit": limit, "remaining": left, "reset": 1790189052}, "graphql": {"limit": gl, "remaining": 0}}})
        return lambda *a: classic if not a else Out(body)
    t = F.write_path_line(run=run_with(60, 12, 0))
    assert t.startswith("GITHUB WRITE PATH: THROTTLED") and "core limit 60/h with 12 left until 18:44 UTC" in t and "GraphQL limit 0" in t, t
    assert "NO GitHub call this run" in t and "drafts/<repo>-<slug>.md" in t and "says OPEN" in t
    assert F.write_path_line(run=run_with(5000, 4990, 5000)).startswith("GITHUB WRITE PATH: OPEN")
    assert F.write_path_line(run=lambda *a: classic if not a else Out("not json")).startswith("GITHUB WRITE PATH: OPEN"), "an unreadable limit is not a throttle"
    assert F.throttle_line(run=run_with(999, 0, 0)).startswith("GITHUB WRITE PATH: THROTTLED"), "below 1000 is throttled"
    print("PASS throttle: a 60/h core limit puts THROTTLED in the brief with the numbers, the reset time and the order to draft, "
          "not call; 5000 reads OPEN; an unreadable limit reads OPEN")


def test_the_board_line_is_measured_and_tells_every_agent_to_add_and_move():
    """Owner, 2026-09-24: the Kanban is not one agent's job - "all agents are needed to work on kanban and updating
    it". So every brief carries what is on the board FOR THIS AGENT and the order to add what it starts and move
    what moves. An agent with nothing on the board is told to add; one whose cards all sit still is told to move or
    explain; a box without the tool says nothing (never a false order)."""
    class Out:
        def __init__(self, stdout): self.stdout = stdout
    F.BOARD_BIN = __file__                      # something that exists, so the line is produced
    empty = F.board_line(run=lambda *a: Out("\nBacklog (0)\n\nBuilding (0)\n\nMerged / live (0)\n"))
    assert "THE BOARD (0 card(s) yours)" in empty, empty
    assert "add the one thing you are doing now" in empty and "swarm-board add" in empty
    stuck = F.board_line(run=lambda *a: Out("\nBacklog (3)\n\nBuilding (0)\n\nIn review (PR open) (0)\n"))
    assert "THE BOARD (3 card(s) yours: Backlog 3)" in stuck, stuck
    assert "Nothing of yours is moving" in stuck
    busy = F.board_line(run=lambda *a: Out("\nBacklog (1)\n\nBuilding (2)\n\nIn review (PR open) (1)\n"))
    assert busy.startswith("THE BOARD (4 card(s) yours") and "Nothing of yours" not in busy, busy
    assert "swarm-board move" in busy and "the same run it moves" in busy
    assert F.board_line(run=lambda *a: Out("")) == "", "no answer from the tool says nothing"
    F.BOARD_BIN = "/nonexistent/swarm-board"
    assert F.board_line() == "", "a box without the board says nothing"
    print("PASS board line: every brief carries this agent's own cards and the order to add what it starts and move "
          "what moves; empty and stuck boards get their own sentence; a box without the tool stays silent")

def test_an_agent_is_told_to_carry_two_or_three_cards_at_once():
    """Owner, 2026-09-24: "why in kanban only 2 are building now, and we have 13 agents 100% builders but not doing
    building in parallel? ... tell agents to work on multiple tasks in parallel ... without compromising the quality".

    The agents were not idle - the boards carried 50 and 46 cards in review - but each held ONE card and flipped it to
    "In review" the moment a pull request opened, so a whole swarm of builders showed "Building 2". A run is one
    process, so the parallelism that is real is work in hand: two or three cards at once, so that while one waits on a
    maintainer another is being built. Below the floor the agent is told to pull the difference from Backlog THIS RUN;
    above the ceiling it is told that is thrash. The quality half is stated in the same breath and is not negotiable:
    reads batch through rai-par, every WRITE stays one at a time, and no pull request goes out untested."""
    class Out:
        def __init__(self, stdout): self.stdout = stdout
    F.BOARD_BIN = __file__
    one = F.board_line(run=lambda *a: Out("\nBacklog (4)\n\nBuilding (1)\n\nIn review (PR open) (2)\n"))
    assert one.startswith("WORK IN PARALLEL"), one
    assert "you have 1 card(s) in Building" in one and f"the rule is {F.WIP_MIN}-{F.WIP_MAX}" in one
    assert "Pull 1 more from Backlog" in one, one
    assert "keep every WRITE one at a time" in one and "never open a" in one, "the quality half travels with it"
    none = F.board_line(run=lambda *a: Out("\nBacklog (2)\n\nBuilding (0)\n\nIn review (PR open) (0)\n"))
    assert "Pull 2 more from Backlog" in none, none
    at_floor = F.board_line(run=lambda *a: Out("\nBacklog (1)\n\nBuilding (2)\n\nIn review (PR open) (1)\n"))
    assert "WORK IN PARALLEL" not in at_floor, "two in hand already obeys the rule"
    over = F.board_line(run=lambda *a: Out("\nBacklog (1)\n\nBuilding (5)\n\nIn review (PR open) (1)\n"))
    assert over.startswith("You hold 5 cards in Building") and "thrash" in over, over
    assert "Pull" not in over.split("THE BOARD")[0], "over the ceiling is never told to pull more"
    print("PASS parallel work: an agent under the floor is told how many to pull from Backlog this run and that "
          "writes stay one at a time; at the floor it is left alone; over the ceiling it is told to finish, not start")


GOOD_SPEC = """## What it is
A settlement-receipt verifier for the Tollstile pay-per-call runtime, called by the maintainer's own CI.

## Where Nano comes in
It proves a Nano (XNO) send block settled a call, so a seller can charge per request without an EVM wallet.

## Interface
`verify(block_hash: str, expect_raw: int, account: str) -> Receipt`
Returns `Receipt(settled: bool, amount_raw: int, height: int)`.
Raises `NotFound` when the node has no such block, `Mismatch` when the amount differs from expect_raw.

## Data
Node reply: `{"block_account": "nano_3abc", "amount": "1000000000000000000000000", "confirmed": "true", "height": 42}`
Receipt returned: `{"settled": true, "amount_raw": 1000000000000000000000000, "height": 42}`

## Workflow (pseudocode)
```
verify(block_hash, expect_raw, account):
    reply = rpc("block_info", json_block=true, hash=block_hash)
    if reply has key "error":            raise NotFound(block_hash)
    if reply["confirmed"] != "true":     return Receipt(settled=false, amount_raw=0, height=0)
    if int(reply["amount"]) != expect_raw: raise Mismatch(int(reply["amount"]), expect_raw)
    if reply["block_account"] != account: raise Mismatch(reply["block_account"], account)
    return Receipt(settled=true, amount_raw=int(reply["amount"]), height=int(reply["height"]))
```

## Acceptance tests
- GIVEN a confirmed block of 10^24 raw WHEN verify(hash, 10**24, account) THEN Receipt(settled=True, amount_raw=10**24, height=42)
- GIVEN an unconfirmed block WHEN verify(hash, 10**24, account) THEN Receipt(settled=False, amount_raw=0, height=0)
- GIVEN the node replies {"error": "Block not found"} WHEN verify(hash, 1, account) THEN raises NotFound

## Runtime
python 3.11, standard library only, no third-party dependency.

## Out of scope
No signing, no sending, no wallet handling, no retry loop.

## Where it ships
Repository `nano-settlement-verify`, published, and the Tollstile maintainer is told on their issue #44.
"""


def test_a_build_spec_is_refused_until_a_builder_could_finish_it_without_asking():
    """Owner, 2026-09-24: agents write "technical pseudo code, with all technical workflows ... enough for claude
    agent to make it 100%, and let them write it with zero ambiguity", and a cloud builder turns it into the repo.

    That only works if the spec is complete BEFORE it is sent: the builder runs in a sandbox and cannot ask a
    question, so a spec that is 90% clear is not 90% useful - it is a wasted run. Every refusal here is one question
    the builder would otherwise have had to come back and ask."""
    ok = ("build: Nano settlement receipt verifier", GOOD_SPEC)
    F.spec_check(*ok)                                     # complete: passes silently

    def refused(title, body, needle):
        try:
            F.spec_check(title, body)
        except F.Refused as ex:
            assert needle in str(ex), (needle, str(ex))
            return
        raise AssertionError(f"not refused: {needle}")

    assert F.spec_check("announce: a thing went live", "short") is None, "only a build: issue is a spec"
    refused("build: a verifier", "## What it is\nA verifier.\n", "is missing")
    refused("build: a verifier", GOOD_SPEC.replace("## Out of scope", "## Notes"), "`## out of scope`")
    refused("build: a verifier", GOOD_SPEC.replace("```", "", 2), "there is no pseudocode")
    refused("build: a verifier", GOOD_SPEC.replace("python 3.11, standard library only, no third-party dependency.",
                                                   "whatever fits best."), "must name the language")
    thin = GOOD_SPEC.replace("- GIVEN an unconfirmed block WHEN verify(hash, 10**24, account) THEN Receipt(settled=False, amount_raw=0, height=0)\n", "")
    thin = thin.replace("- GIVEN the node replies {\"error\": \"Block not found\"} WHEN verify(hash, 1, account) THEN raises NotFound\n", "")
    refused("build: a verifier", thin, "acceptance test")
    refused("build: a verifier", GOOD_SPEC.replace("no retry loop.", "no retry loop, etc."), "hides behind `etc`")
    refused("build: a verifier", GOOD_SPEC.replace("sending, no wallet handling", "sending, TBD"), "`tbd`")
    # every mention stripped, not a few: the spec's own heading says "Nano" and would have satisfied the check
    no_nano = re.sub(r"(?i)\b(nano|xno)\b", "USDC", GOOD_SPEC).replace("nano_3abc", "0xabc")
    refused("build: a verifier", no_nano, "where Nano (XNO) is in this")
    assert "## Acceptance tests" in F.SPEC_TEMPLATE and "zero" not in F.SPEC_TEMPLATE.lower()
    assert F.SPEC_TEMPLATE.startswith("build: "), "the template shows the prefix that makes it a spec"
    print("PASS build spec: a complete spec passes; a missing section, no pseudocode, no runtime, too few "
          "acceptance tests, a hedging word and a spec with no Nano in it are each refused, naming what to fix")


GOOD_PATCH = """## Upstream
michielpost/x402-dev - their issue #101 asks for a settlement network that needs no gas token.

## What is missing
Their seller example can only take USDC on Base, so a seller without an EVM wallet cannot use the project at all.
Their README calls that out as a known limitation.

## The change
`src/rails/index.ts`: register a second rail beside the existing `base` entry.
`src/rails/nano.ts` (new): implement the same `Rail` interface - `quote()`, `verify()`, `refund()` - against a Nano
node's `block_info`, integer raw arithmetic only.
`README.md`: one row in the rails table.

## Acceptance
- `pnpm test` passes with the two new cases in `test/rails.nano.test.ts`
- `pnpm run example -- --rail nano` prints a settled receipt against their fixture node

## Why they want it
Their issue #101: "we keep hearing from sellers who do not want to hold gas". Nano (XNO) settles with no gas token
and no per-transfer fee, which is the case they are asking for.
"""


def test_a_patch_request_is_refused_until_a_worker_could_write_it_upstream():
    """Owner, 2026-09-24: 192 upstream pull requests in 14 days, 11 merged. The agents pick the right targets; the
    diff is what loses. So the agent writes the case and the cloud worker writes the patch - which only works if the
    request names the upstream, the files, how the maintainer verifies it, and evidence from their own project.

    The refusal that matters most is the self-owned one: a pull request to our own account reaches no maintainer and
    merges nothing, which this swarm already did 35 times before it was caught."""
    F.patch_check("patch: add a Nano rail", GOOD_PATCH)          # complete: passes silently

    def refused(body, needle, title="patch: add a Nano rail"):
        try:
            F.patch_check(title, body)
        except F.Refused as ex:
            assert needle in str(ex), (needle, str(ex))
            return
        raise AssertionError(f"not refused: {needle}")

    assert F.patch_check("build: something else", "short") is None, "only a patch: issue is a patch request"
    refused("## Upstream\nthem/repo\n", "missing")
    refused(GOOD_PATCH.replace("michielpost/x402-dev", "PANDeveloper001/x402-dev"), "account we own")
    refused(GOOD_PATCH.replace("michielpost/x402-dev", "dhyabi2/x402-dev"), "account we own")
    refused(GOOD_PATCH.replace("michielpost/x402-dev - their issue #101 asks", "their project asks"),
            "must name the repository as `owner/repo`")
    thin = GOOD_PATCH.replace("- `pnpm run example -- --rail nano` prints a settled receipt against their fixture node\n", "")
    refused(thin, "at least 2 are needed")
    refused(GOOD_PATCH.replace("one row in the rails table.", "one row in the rails table, etc."), "hides behind")
    refused(re.sub(r"(?i)\b(nano|xno)\b", "USDC", GOOD_PATCH), "what Nano (XNO) does in this change")
    assert F.PATCH_TEMPLATE.startswith("patch: ") and "## Acceptance" in F.PATCH_TEMPLATE
    print("PASS patch request: a complete request passes; a missing section, an upstream that is ours, no owner/repo, "
          "too few acceptance lines, a hedging word and no Nano are each refused, naming what to fix")


GOOD_HEAVY = """## What it is
The journal on this box has drifted: `swarm-proof` rebuilds from it and now publishes two adoptions whose links
404, while three real merges are missing entirely. The rebuild logic and the journal's own retention interact and I
cannot tell which is dropping what.

## Why it needs the stronger model
Three pieces interact - the retention trim, the collector's dedupe key and the rebuild's link check - and the
symptom appears in none of them alone. Every run I spend on it costs the pool and ends with a different guess, and
a wrong fix here publishes false proof to strangers, which is worse than publishing nothing.

## What I already tried
Run 41: re-ran the collector by hand, 299 commit facts appeared, the two dead links stayed. Run 44: raised retention
on this box and rebuilt - no change, so it is not the trim. Run 47: read the dedupe key and believed it was the
idempotency key, rewrote it, and the suite went red in four places, so I reverted it. I have ruled out the trim and
I cannot hold the other two in one run.

## What done looks like
`swarm-proof` rebuilds with zero 404 links, the three merged pull requests appear, and the suite is green.
"""


def test_a_heavy_escalation_is_for_critical_work_and_one_at_a_time():
    """Owner, 2026-09-24: agents may escalate heavy work to the stronger model, but "only critical consuming work
    decided by agent, not any work". "Only ask when it matters" is not a rule anybody can be held to, so the limit
    is structural - one open escalation per agent - and the agent must say what it already tried. Work nobody has
    attempted is not heavy work; it is work not started."""
    none_open = Forge()
    none_open.issues_reply = []
    F.heavy_check("heavy: swarm-proof publishes dead links", GOOD_HEAVY, http=lambda *a, **k: (200, []))

    def refused(body, needle, http=lambda *a, **k: (200, [])):
        try:
            F.heavy_check("heavy: swarm-proof publishes dead links", body, http=http)
        except F.Refused as ex:
            assert needle in str(ex), (needle, str(ex))
            return
        raise AssertionError(f"not refused: {needle}")

    assert F.heavy_check("build: a repo", "short", http=lambda *a, **k: (200, [])) is None, "only heavy: is checked"
    refused("## What it is\nsomething\n", "missing")
    refused(GOOD_HEAVY.replace(GOOD_HEAVY.split("## What I already tried")[1].split("## What done")[0],
                               "\nNothing yet.\n\n"), "what you actually attempted")
    refused(GOOD_HEAVY.replace("The journal on this box has drifted", "I need a new repository that"),
            "goes through `build:`")
    refused(GOOD_HEAVY.replace("The journal on this box has drifted",
                               "I want a pull request on their repo, upstream, that"), "goes through `patch:`")

    # one at a time: an open escalation of this agent's own blocks the next
    open_one = [{"number": 77, "title": f"[{F.ME}] heavy: an earlier one",
                 "labels": [{"name": "heavy-request"}]}]
    refused(GOOD_HEAVY, "you already have an open escalation, #77", http=lambda *a, **k: (200, open_one))
    # somebody else's open escalation does not block this agent
    other = [{"number": 78, "title": "[someone-else] heavy: theirs", "labels": [{"name": "heavy-request"}]}]
    F.heavy_check("heavy: swarm-proof publishes dead links", GOOD_HEAVY, http=lambda *a, **k: (200, other))
    # a forge that cannot be read never stops an agent asking for help
    def broken(*a, **k):
        raise OSError("forge down")
    F.heavy_check("heavy: swarm-proof publishes dead links", GOOD_HEAVY, http=broken)
    print("PASS heavy escalation: a real one passes; a missing section, nothing tried, a disguised build or patch, "
          "and a second one while the first is open are refused; another agent's does not block, and an unreadable "
          "forge never blocks")


def test_the_three_doors_are_in_the_brief_not_only_in_a_pinned_issue():
    """Measured 2026-09-24: the doors opened at 10:40, were announced in a pinned issue assigned to all fifteen
    agents, and SEVEN runs finished across six agents with not one spec, patch or escalation written.

    That is this swarm's oldest mistake, written down twice already: the merge queue lived in step 2 of a 300-line
    AGENTS.md and the lead merged nothing for three runs; the write-path belief outlived its token by a day because
    it lived in text. Only the brief is read. So the doors are in the brief, with the swarm's own count beside them -
    and while that count is zero, the line says so in the first words, because a line that reads like an
    advertisement is skipped and a line that reads like a measurement is not."""
    class Out:
        pass

    def forge(counts):
        def go(method, path, body=None):
            for label, n in counts.items():
                if f"labels={label}" in path:
                    return 200, [{"number": i, "labels": [{"name": label}]} for i in range(n)]
            return 200, []
        return go

    empty = F.doors_line(http=forge({"build-spec": 0, "patch-request": 0, "heavy-request": 0}))
    assert empty.startswith("THE CLOUD WORKER - NOTHING HAS BEEN SENT TO IT YET"), empty
    for door in ("build:", "patch:", "heavy:"):
        assert door in empty, door
    assert "spec-template" in empty and "patch-template" in empty and "heavy-template" in empty
    assert "11 of 192" in empty, "the patch door carries the number that justifies it"

    some = F.doors_line(http=forge({"build-spec": 2, "patch-request": 1, "heavy-request": 0}))
    assert some.startswith("THE CLOUD WORKER (2 spec / 1 patch / 0 escalation"), some
    assert "NOTHING HAS BEEN SENT" not in some

    def broken(*a, **k):
        raise OSError("forge down")
    assert F.doors_line(http=broken) == "", "a forge that cannot be read never puts a false count in the brief"
    print("PASS the three doors: the brief carries build/patch/heavy with this swarm's own count; a swarm that has "
          "sent nothing is told so in the first words; an unreadable forge says nothing rather than a false zero")


if __name__ == "__main__":
    test_the_three_doors_are_in_the_brief_not_only_in_a_pinned_issue()
    test_a_heavy_escalation_is_for_critical_work_and_one_at_a_time()
    test_a_patch_request_is_refused_until_a_worker_could_write_it_upstream()
    test_a_build_spec_is_refused_until_a_builder_could_finish_it_without_asking()
    test_an_agent_is_told_to_carry_two_or_three_cards_at_once()
    test_the_board_line_is_measured_and_tells_every_agent_to_add_and_move()
    test_throttled_account_is_measured_and_the_brief_orders_drafts_not_calls()
    test_announce_is_checked_before_the_issue_exists_and_the_brief_measures_x()
    test_the_write_path_is_measured_in_every_brief()
    test_the_open_discussion_is_in_the_brief_until_the_agent_has_spoken()
    test_every_meeting_is_followed_by_a_pinned_open_discussion()
    test()
    test_meeting()
    test_a_broken_forge_tool_is_never_silent()
    test_lead_brief_puts_the_merge_queue_first()
