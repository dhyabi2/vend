#!/usr/bin/env bash
# Heartbeat: generates real progress events so the watcher sees activity
# Called by cron every 5 minutes
set -euo pipefail

cd /root/vend
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Log treasury + health
TREASURY=$(python3 bin/vend-treasury-check.py 2>/dev/null || echo "unknown")
HEALTH=$(python3 bin/probe-directories.py 2>/dev/null | tail -1 || echo "health check failed")

echo "[$TIMESTAMP] HEARTBEAT treasury=$TREASURY health=$HEALTH" >> /root/vend/heartbeat.log

# Keep only last 500 lines
tail -n 500 /root/vend/heartbeat.log > /tmp/hb.tmp && mv /tmp/hb.tmp /root/vend/heartbeat.log

echo "ok"
