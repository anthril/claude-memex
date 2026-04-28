---
description: Install Memex Autopilot — scaffold the .memex/.autopilot/ state store and verify prerequisites
argument-hint: "[--dry-run] [--with-cron]"
allowed-tools: Read, Glob, Grep, Bash
---

# /memex:autopilot-install

Install the Memex Autopilot: continuous-loop multi-agent orchestration that scans the Memex backlog (open questions, project-owner actions), dispatches specialist subagents in worktrees, and routes their reports to `.memex/.inbox/` for human review. The state store is `.memex/.autopilot/`.

## Usage

```
/memex:autopilot-install            # full install
/memex:autopilot-install --dry-run  # show what would be done; write nothing
/memex:autopilot-install --with-cron # also register scheduled-tasks (optional)
```

## Prerequisites

- Memex initialised in this project (`memex.config.json` or `.memex/` exists). If not, run `/memex:init <profile>` first.
- Python 3.10+ on PATH.

The plugin's hook scripts (`autopilot-write-guard.py`, `autopilot-subagent-stop.py`, `autopilot-notify.py`, `autopilot-budget-reset.py`) and helper modules (`autopilot_state.py`, `autopilot_worker.py`) ship with the memex plugin and are guaranteed to exist when the plugin is installed.

## Behaviour

Numbered steps; execute in order.

1. **Parse args.** Look for `--dry-run` and `--with-cron` flags in `$ARGUMENTS`. Default: live install, no cron registration.

2. **Verify prerequisites.** Use the `Bash` tool to run:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/installer.py" --check
   ```
   If any check fails, print the missing items and abort.

3. **Scaffold state store.** If `--dry-run` was passed, skip; otherwise:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/installer.py" --apply
   ```
   This creates `.memex/.autopilot/{state.json,BUDGET,history.jsonl,runs/,locks/,digests/}` and `.memex/.inbox/{,quarantine/}` with the schema_version=1 default state and budget=30.

4. **Self-test.** Always run (even on `--apply`) to verify the install:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/installer.py" --self-test
   ```
   Expected: prints `OK: state load/save/append cycle; budget read/decrement; pause toggle`.

5. **Optional cron registration.** Only if `--with-cron` was passed and the `mcp__scheduled-tasks__create_scheduled_task` tool is available, register two scheduled tasks:
   - **Heartbeat**: cron `0 9,12,15 * * 1-5` running `/memex:autopilot-tick`
   - **Daily budget reset**: cron `1 0 * * *` running `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/autopilot-budget-reset.py`

   For each task, capture the returned `taskId` and write it to `.memex/.autopilot/scheduled-task-ids.json` so `/memex:autopilot-uninstall` can deregister them.

   If the MCP tool is not available, print: "Skipping cron registration (mcp__scheduled-tasks not available). Run install with --with-cron once the MCP server is connected."

6. **Print install summary.** Output a single block:

   ```
   ## Memex Autopilot — install complete
   - State store: .memex/.autopilot/  (schema_version=1, budget=30 sessions/day)
   - Inbox lane: .memex/.inbox/
   - Hooks: PreToolUse / SubagentStop / Notification / cron (autopilot-* scripts)
   - Cron schedule: <entries with task IDs, or "not registered (use --with-cron)">
   - Locked-paths denylist: read from memex.config.json#/autopilot/locked_paths
   - Kill switch: touch .memex/.autopilot/PAUSED  (or run /memex:autopilot-pause)

   Next step: run `/memex:autopilot-tick` to fire one coordinator pass manually,
   or wait for the cron heartbeat (if registered).
   ```

7. **Idempotency.** If state.json already exists with schema_version=1, skip step 3 and print "State store already initialised". To force re-init, the user can `rm -rf .memex/.autopilot` (the wizard does NOT do this).

## Failure modes

- Missing prerequisite → list it, abort, exit 1.
- Python import error → print traceback, abort.
- `--with-cron` requested but MCP tool absent → warn and continue without cron.

## See also

- [`docs/autopilot/state-store-schema.md`](../docs/autopilot/state-store-schema.md) — what the wizard creates
- [`docs/autopilot/worker-contract.md`](../docs/autopilot/worker-contract.md) — what the coordinator dispatches
- `/memex:autopilot-tick` — manually fire one tick after install
- `/memex:autopilot-status` — check current loop state
- `/memex:autopilot-pause` / `resume` / `uninstall` — lifecycle
