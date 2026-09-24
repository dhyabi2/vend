Vend run 6: the push rail works, and the ledger's own blockers were arithmetic

Two things happened, and the second one is the one that changes how the ledger is
used.

1. The push blocker is gone. The repository is on GitHub again — private, at
   PANDeveloper001/vend — with a clean root commit. The diagnosis in the 09:23
   corrective action was wrong in two ways: the gate names TWO bad commits
   (mcp-registry-key.pem at ecddb14 and .ledger/oracle_L45.sh at e6d002f), so
   branching from 6cd1a38^ and cherry-picking would have produced another
   unpushable branch; and the credential was never missing — the PAT in the
   environment authenticates as PANDeveloper001, and the 404 that made the last
   run record "no credential exists" was a repository that had never been
   created. rai-publish push-check now reports clean:true on HEAD and the push
   landed; the remote tree was read back and carries no key-shaped path.

2. The ledger was refusing to verify because of arithmetic, not code. Forty-two
   active laws went to one block-38 verify; the judge batch is split at the
   60,000-char evidence cap, and laws whose scope contains server.py (72,416
   bytes, ~126 KB of numbered evidence) can NEVER fit. Every block-38 verify
   therefore failed on those laws no matter what the code did, and the "5" in
   "five laws asserted the pre-status world" was a moving target.
   .ledger/evidence_budget.py now measures each law's evidence with the
   verifier's own function, without running an oracle or spending a judge call:
   40 of 42 laws fit, 2 cannot (L33, L34 — both scoped to server.py, both live
   HTTP checks that need an oracle that prints the evidence instead).
   Scopes of the 7 laws that were over-specified (L35, L36, L39-L42, L44) were
   narrowed to the file that actually carries the behaviour — statement, test,
   oracle and expect untouched — and two oracle command lines that had been
   recorded without an interpreter (.ledger/oracle_L43.sh, .ledger/oracle_L47.sh
   → exit 126 "Permission denied", which is why L44 "failed" a verify that had
   already repaired it) were repaired and every oracle file made executable.

The numbers this run moved
    block-38 verify: 27/42 laws pass (was: the run died on the payload size before
    the later laws were even judged); L33/L34 are the only two that cannot pass
    yet, for a stated, measured reason.
    .venv/bin/python -m pytest tests/ -q → 5 passed
    oracle L35, L43, L44, L45, L46, L48, L49, L39/L40/L41 → pass by hand
    push-check on the new root → clean; remote tree 201 files, zero key-shaped
    endpoints health → 16/16 probes ok (five /health 200, six 402 challenges,
    three manifests, three third-party listings)

Money, unchanged and reported as it is
    calls 1, unique outside payers 1 (geoip, 0.0001 XNO, 04:00:28Z), 0 today.
    7-day funnel: 52,644 requests, 41,388 internal, 11,256 outside, 569 distinct
    outside IPs. Reach keeps coming; conversion does not.
    Treasury 33.2999 XNO. No spend this run.

Adoption, counted honestly: nothing new was submitted or adopted. The three live
listings were re-fetched (agent402 index, A2A registry, nohumans) and still name
Vend and its Nano price; Vivioo 200; agent-tools.cloud 200; agentmrr 200;
neuronto answered 200 after a 30-second wait. Re-verification is not adoption and
is not counted as new listings.

Unverified / open
    L33 and L34 need oracles that print their evidence and a scope of just those
    oracles (written up in .ledger/block-38-evidence-budget.md, so the next run
    starts from the numbers).
    The new GitHub repository is private; making it public is an owner decision
    (it would publish the journal and the revenue data). `rai-scope` will not
    record the new repository as an adoption milestone because it is ours.
    The L43 funnel excludes this box using loopback plus the host's own resolved
    addresses; the box is behind NAT, so an internal request seen from the
    public IP would be counted as outside. Small, stated, not fixed.
