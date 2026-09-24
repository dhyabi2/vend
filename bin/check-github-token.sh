#!/bin/sh
# Presence check: does the shared environment carry a GitHub token?
# Never prints a value. Exit 0 when present, 1 when absent.
set -a
. /root/.hermes/.env 2>/dev/null
set +a
if [ -n "${GITHUB_TOKEN:-}" ] || [ -n "${GH_TOKEN:-}" ]; then
    echo "github token: present in /root/.hermes/.env"
    exit 0
fi
echo "github token: absent from /root/.hermes/.env and from this session"
exit 1
