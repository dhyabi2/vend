#!/usr/bin/env bash
# Vend git credential helper: give git the GitHub PAT from the environment.
#
# Why: the clone had no credential helper at all (git config credential.helper
# empty, no ~/.git-credentials, no gh), so `git ls-remote origin` died with
# "could not read Username for 'https://github.com'" — for every run, on every
# remote, including the repositories that this account's PAT can write to. The
# token was never missing; the helper was. Request #1 (a push key) sat open for
# days on the wrong diagnosis.
#
# The token is read from the environment (rai tooling sources ~/.hermes/.env) and
# printed only to git's own credential protocol. No file is written, nothing is
# copied, no key is printed, rotated or edited.
#
# Usage (per call, nothing persisted):
#   git -c credential.helper="/root/vend/bin/git-credential-env.sh" ls-remote origin
#
# The wrapper rai-ship does this for push/pull/ls-remote.
set -euo pipefail

[ "${1:-}" = "get" ] || exit 0

if [ -z "${GITHUB_TOKEN:-}" ] && [ -r /root/.hermes/.env ]; then
    # Source only to get the token into this process; never echo it.
    set -a
    # shellcheck disable=SC1091
    . /root/.hermes/.env
    set +a
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "git-credential-env.sh: no GITHUB_TOKEN in the environment (rai tooling sources ~/.hermes/.env)" >&2
    exit 1
fi

printf 'protocol=https\nhost=github.com\n'
printf 'username=%s\n' "${NANO_AGENT_GITHUB_USER:-x-access-token}"
printf 'password=%s\n' "$GITHUB_TOKEN"