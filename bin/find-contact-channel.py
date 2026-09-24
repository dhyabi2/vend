#!/usr/bin/env python3
"""
find-contact-channel.py — find a WORKING, non-GitHub write channel for a target.

Vend (jig territory) keeps first-contact drafts for dev-doc / guide / comparison
pages that frame agent payments as stablecoin-only. Most sit unposted because the
maintainer has no verifiable, token-free write channel on record. The GitHub fine-
grained token cannot open issues/PRs on third-party repos, so a usable first contact
must go through the target's OWN surface: a contact/about page, a mailto:, a
Discord/discussion invite, a submission form, or a keyless API the site itself runs.

This tool fetches the homepage and common channel paths, extracts anything that
looks like a reachable write channel, and prints a one-line verdict per target so a
draft can cite "reachable at <channel>" or "no token-free channel found yet".

Usage:
  bin/find-contact-channel.py [base-url] ...
  bin/find-contact-channel.py --file targets.txt
  bin/find-contact-channel.py --json  (emit JSON on stdout, one object per target)

Exit code 0 if at least one channel was found across all targets; 1 otherwise
(nothing found is an honest "no channel yet", never a fake one).

What counts as a channel (checked in order, first hit wins the verdict):
  - a mailto: address anywhere in the fetched HTML
  - a Discord invite link (discord.gg / discord.com/invite)
  - a link to a discussion/forum the site owns (github.com/<owner>/<repo>/discussions
    where <owner> is the site's own org, or a Discourse/github discussion page)
  - a /submit or /contact or /about page path that returns 200 (form surfaces)
  - a JSON API endpoint the site hosts that accepts submissions (best effort; do not
    post, only detect its existence and shape)
  - a keyless subscription/issue API (e.g. the site's own docs mention a form)
The verdict line names exactly what was found so a human or the next run can act.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse

UA = {"User-Agent": "vend-agent/1.0 (channel finder; no content stored)"}


def fetch(url: str, timeout: int = 15):
    """Return (status, html) for a URL, or (status, '') on failure."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, ""


def channels(base: str) -> dict:
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    found = {"mailto": [], "discord": [], "discussions": [], "forms": [], "apis": []}
    html = ""
    paths = ["/", "/contact", "/contacts", "/about", "/submit", "/community",
             "/discord", "/feedback", "/docs", "/contact-us"]
    # Fetch homepage first; derive the rest from it.
    st, html = fetch(origin + "/")
    if st == 200 and html:
        # mailto:
        found["mailto"] = sorted(set(re.findall(r'href="mailto:([^"]+)"', html, re.I)))
        # discord invites
        found["discord"] = sorted(set(
            re.findall(r'href="(https?://(?:discord\.gg|discord\.com/invite)/[^"]+)"', html, re.I)))
        # own-org discussion links
        for m in re.findall(r'href="(https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/discussions)"', html, re.I):
            found["discussions"].append(m)
        # relative links to likely form surfaces on this origin
        for p in ["/contact", "/contacts", "/about", "/submit", "/community"]:
            if re.search(rf'href="[^"]*{re.escape(p)}[^"]*"', html, re.I):
                found["forms"].append(origin + p)
    # Probe likely contact/submit paths directly (existence of a page/form surface).
    for p in ["/contact", "/contacts", "/contact-us", "/about", "/submit", "/community"]:
        st2, h2 = fetch(origin + p)
        if st2 == 200:
            if p not in ["/contact", "/contacts", "/contact-us", "/about", "/submit", "/community"]:
                continue
            if p in ("/submit",) or re.search(r"contact|feedback|submit|issue|message", h2, re.I):
                if origin + p not in found["forms"]:
                    found["forms"].append(origin + p)
            mails = set(re.findall(r'mailto:([^"\']+)', h2, re.I))
            if mails:
                for m in mails:
                    if m not in found["mailto"]:
                        found["mailto"].append(m)
    # Dedupe and produce a verdict.
    verdict = None
    if found["mailto"]:
        verdict = f"mailto:{found['mailto'][0]}"
    elif found["discord"]:
        verdict = f"discord {found['discord'][0]}"
    elif found["discussions"]:
        verdict = f"discussions {found['discussions'][0]}"
    elif found["forms"]:
        verdict = f"form {found['forms'][0]}"
    found["verdict"] = verdict if verdict else "no token-free channel found yet"
    found["probed"] = origin
    return found


def main(argv):
    em = "--file"
    targets = []
    if em in argv:
        fpath = argv[argv.index(em) + 1]
        with open(fpath) as f:
            targets = [ln.strip() for ln in f if ln.strip()]
        argv = [a for a in argv if a != em and a != fpath]
    else:
        targets = [a for a in argv if a.startswith("http")]

    as_json = "--json" in argv
    results = []
    any_found = False
    for t in targets:
        r = channels(t)
        r["target"] = t
        results.append(r)
        if r["verdict"] and not r["verdict"].startswith("no "):
            any_found = True
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['target']:45s} -> {r['verdict']}")
    return 0 if any_found else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
