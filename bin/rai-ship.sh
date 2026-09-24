#!/usr/bin/env bash
# Vend's one push path. It never bypasses a rail: the same gate `git push` is
# held to (rai-publish push-check on the exact HEAD) runs here first, and the
# push is refused unless that check is clean and fresh.
#
# Why this exists
#   1. Publishing used to be attempted by hand from the CLI, and the run that
#      pushed commit 6cd1a38 into the tracked tree proved how expensive that is.
#      A shell alias cannot be audited; this can, and every step is logged.
#   2. The clone's git forges were used on very long-lived branches that had
#      diverged from their upstream in both directions, so `git push` had no
#      fast-forward answer. A push whose upstream is behind is an honest refusal
#      here (no --force, ever, per the agent's fixed limits) — this script says
#      so instead of trying and failing at the forge.
#   3. The credential helper the clone was missing is supplied here, from the
#      environment, without writing a secret anywhere.
#
# Usage:
#   bin/rai-ship.sh status                 # branch, HEAD, upstream, what a push would send
#   bin/rai-ship.sh check                  # run rai-publish push-check on HEAD
#   bin/rai-ship.sh push [--dry-run]       # check, then fast-forward push
#   bin/rai-ship.sh ship [-m "message"]    # commit staged work (gate first), then push
#
# Exit codes: 0 ok, 2 refused before touching the network, 3 nothing to do.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

GIT=(git)
HELPER="$REPO/bin/git-credential-env.sh"
[ -x "$HELPER" ] || { echo "refused: $HELPER is missing or not executable" >&2; exit 2; }
net_git() { GIT_TERMINAL_PROMPT=0 git -c credential.helper="$HELPER" "$@"; }

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
head_sha="$(git rev-parse HEAD 2>/dev/null || true)"

show_status() {
    echo "branch:   ${branch:-none}"
    echo "HEAD:     ${head_sha:-none}"
    if upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
        echo "upstream: $upstream"
        ahead="$(git rev-list --count "$upstream..HEAD" 2>/dev/null || echo '?')"
        behind="$(git rev-list --count "HEAD..$upstream" 2>/dev/null || echo '?')"
        echo "to send:  $ahead commit(s); upstream is $behind ahead"
        [ "${behind:-0}" = "0" ] || echo "NOTE:     upstream has diverged; this script will refuse a non-fast-forward push"
    else
        echo "upstream: none (a first push creates it)"
    fi
    echo "remote:   $(git remote get-url origin 2>/dev/null || echo none)"
}

run_check() {
    echo "-- rai-publish push-check (the gate of record)"
    if rai-publish push-check --repo "$REPO" 2>&1 | tee /tmp/rai-ship-check.json; then
        grep -q '"clean": true' /tmp/rai-ship-check.json || {
            echo "refused: push-check did not report clean" >&2; return 2; }
    else
        echo "refused: the secret gate refused this HEAD; nothing is pushed" >&2
        return 2
    fi
    # Belt and braces: name-shaped key files must not be in the tracked tree at
    # all, even if the scan were to miss one.
    if git ls-files | grep -Eq '(^|/)\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|git-credentials$|\.netrc$'; then
        echo "refused: a secret-looking path is tracked:" >&2
        git ls-files | grep -E '(^|/)\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|git-credentials$|\.netrc$' >&2
        return 2
    fi
    echo "-- pushed tree carries no secret-looking path"
    return 0
}

do_push() {
    local dry=""
    [ "${1:-}" = "--dry-run" ] && dry="--dry-run"
    [ -n "$head_sha" ] || { echo "refused: no commits on this branch yet" >&2; return 3; }
    run_check || return 2
    if ! upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
        upstream=""
    fi
    if [ -n "$upstream" ]; then
        behind="$(git rev-list --count "HEAD..$upstream" 2>/dev/null || echo 0)"
        if [ "${behind:-0}" != "0" ]; then
            echo "refused: $upstream is $behind commit(s) ahead; a fast-forward is impossible and force-pushing is" >&2
            echo "         forbidden by the agent's fixed limits. Reconcile by hand (merge/rebase) and re-run." >&2
            return 2
        fi
    fi
    echo "-- push $branch -> origin ${dry:+(dry run)}"
    # shellcheck disable=SC2086
    if net_git push $dry ${upstream:+} -u origin "$branch" 2>&1 | tail -6; then
        echo "-- remote ref: $(net_git ls-remote origin "refs/heads/$branch" | awk '{print $1}')"
        echo "-- local ref:  $head_sha"
        return 0
    fi
    echo "refused: the forge rejected the push" >&2
    return 2
}

case "${1:-status}" in
    status) show_status ;;
    check)  run_check ;;
    push)   do_push "${2:-}" ;;
    ship)
        shift || true
        msg=""
        while [ $# -gt 0 ]; do case "$1" in -m) msg="$2"; shift 2 ;; *) echo "unknown argument: $1" >&2; exit 2 ;; esac; done
        [ -n "$(git status --porcelain)" ] || { echo "nothing to commit"; exit 3; }
        git add -A
        [ -n "$msg" ] || msg="Run close-out $(date -u +%Y-%m-%dT%H:%MZ)"
        echo "-- commit (the pre-commit secret gate runs first)"
        git -c user.name=Vend -c user.email=vend@paypercall.dev commit -m "$msg" || { echo "refused: commit failed" >&2; exit 2; }
        head_sha="$(git rev-parse HEAD)"
        do_push
        ;;
    *) echo "usage: rai-ship.sh {status|check|push [--dry-run]|ship -m MESSAGE}" >&2; exit 2 ;;
esac