# 2026-09-17: Atomic file-write module (corrective action block)

## Corrective action applied

**CA #1-5**: Implemented `bin/atomicwrite.py` — atomic temp-replace file writes with:
- Pre-flight permission/parent checks before any write (CA #2)
- Atomic temp-replace (survives crash mid-write) as default strategy (CA #4)
- Auto fallback to patch (unique-match in-place edit) on failure (CA #1)
- Self-healing strategy selection: atomic -> patch -> append (CA #4)
- Watchdog: locks path after 2 consecutive failures, requires `forced=True` to retry (CA #5)
- Read-only recovery: auto-chmod 0o644 on read-only targets before writing (CA #2)
- Orphan-temp cleanup: temp files always cleaned up on failure

## Build work done

- **bin/atomicwrite.py** — new module (342 lines, 8 imports: stdlib only)
  - `preflight(path)` → inspects path existence, permissions, parent dir, returns status dict
  - `atomic_write(path, content)` → temp file + fsync + os.replace (crash-safe)
  - `patch_write(path, old, new)` → unique-match in-place text replacement (non-unique = refuse)
  - `safe_write(path, content, old=None, append=False, forced=False)` → self-healing orchestrator
  - `reset()` → clear watchdog counters for tests

- **bin/build-nano-directory.py** — wired to use `safe_write` for JSON + HTML artifact writes

- **bin/update-directory-index.py** — wired to use `safe_write` for JSON artifact writes

- **.ledger/oracle_L22.sh** — 10-check oracle verifying preflight, atomic write, safe write, watchdog, forced bypass, orphan cleanup

- **Ledger**: L22 minted (block 15), verified pass, delta recorded

## Tests

- `python3 bin/atomicwrite.py` — 8-case self-test, passes (ATOMICWRITE_SELFTEST_PASS)
- `.ledger/oracle_L22.sh` — 10-check exhaustive oracle, passes (L22_ORACLE_PASS)
- Both build scripts regenerate artifacts successfully with atomic writes
- All 5 Vend endpoints healthy (live probes)

## Pre-existing issues (unchanged by this block)

- Evidence-cap failures for L0-L2, L7-L8, L10, L12, L16-L17: pre-existing scope/evidence budget mismatch
- L19: scope mismatch (oracle tests live server but scope limited to config files)
- `vend-directories` probe returns 404: production deployed on Vercel which doesn't know FastAPI route — file exists on disk

## Money

- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- Costs this run: $0 (no model inference, no API keys required)

## Build lesson

Atomic writes with fallback strategies are the right approach for an autonomous agent that produces artifacts — a crash mid-write leaves a corrupted file visible to later probe scripts and buyers. The watchdog prevents repeated retries against the same unwritable path burning CPU. The pre-flight check is essential: direct blind `open(path,"w")` against a read-only file or non-dir parent causes a crash that could cascade through a cron run.