# Memex Autopilot

> Continuous-loop multi-agent coordinator for Memex projects. Reads
> the existing Memex backlog (open questions and project-owner
> actions), dispatches specialist subagents in worktrees, routes their
> reports to `.memex/.inbox/` for human review. **Nothing is committed
> autonomously.**

The autopilot is an opt-in extension of the memex plugin. It originated
in the [AURORA project](https://github.com/anthril/aurora) and was
generalised when its load-bearing inputs (open questions, project-owner
actions) turned out to be Memex primitives, not Aurora-specific.

## Quickstart

```bash
# 1. Make sure memex is initialised in this project
/memex:init research-wiki         # or any existing memex profile

# 2. Install the autopilot
/memex:autopilot-install          # scaffolds .memex/.autopilot/ + .memex/.inbox/

# 3. Fire a single tick by hand (verify the install)
/memex:autopilot-tick

# 4. Read the result
/memex:autopilot-status
ls .memex/.inbox/                 # routed worker artifacts for human review
```

## What the autopilot does each tick

Each tick is a 6-phase state machine:

| Phase | Reads | Writes |
|---|---|---|
| **PERCEIVE** | `.memex/.open-questions/`, `.memex/.project-owner-actions/`, `git log` | `runs/<run-id>/perceive.json` |
| **PLAN** | perceive.json + `state.json:heuristics` | `runs/<run-id>/<worker-id>/task.json` (one per task) |
| **DISPATCH** | task.json | spawns N background `Agent` workers in worktrees |
| **GATHER** | worker terminal messages | hoists artifacts back to main; synthesises REPORT.md |
| **INTEGRATE** | REPORT.md (one per worker) | `.memex/.inbox/<run-id>/<artifact>.md` (or quarantine) |
| **LEARN** | run summary | bumps `state.json:tick_count` + heuristics; appends `tick_complete` to `history.jsonl` |

A tick that fires while the loop is paused, rate-limited, or out of
budget exits cleanly as a no-op — that's a *successful* tick.

## On-disk layout

```
.memex/
├── .autopilot/                # state store (gitignored)
│   ├── state.json             # current state + heuristics
│   ├── BUDGET                 # plain-int sessions remaining today
│   ├── PAUSED                 # kill switch (presence = halt)
│   ├── RATE-LIMITED           # rate-limit signal
│   ├── history.jsonl          # append-only ledger
│   ├── alerts.jsonl           # Notification-hook alert queue
│   └── runs/<run-id>/         # one directory per coordinator tick
│       └── <worker-id>/
│           ├── task.json      # worker contract
│           ├── REPORT.md      # synthesised report (last line: STATUS: ok|failed|needs-input)
│           └── .done          # SubagentStop marker
├── .inbox/                    # human-review queue (shared with the rest of memex)
│   ├── <run-id>/
│   │   ├── oq-resolution-<slug>.md
│   │   └── owner-action-triage-<slug>.md
│   ├── INBOX.md               # one-line index across all run-ids
│   └── quarantine/            # tasks that failed; excluded from the goal queue
├── .open-questions/           # existing Memex primitive — autopilot reads these
└── .project-owner-actions/    # existing Memex primitive — autopilot reads these
```

The full schema is documented at
[`docs/autopilot/state-store-schema.md`](autopilot/state-store-schema.md).

## Configuration — `memex.config.json`

The autopilot reads an optional `autopilot` block from `memex.config.json`:

```json
{
  "version": "1",
  "profile": "research-wiki",
  "root": ".memex",
  "autopilot": {
    "locked_paths": [
      "docs/charter.md",
      "policies/"
    ],
    "shared_workspaces": [
      "audits/"
    ],
    "task_kinds": {
      "oq-investigate": {
        "specialist": "memex-planner",
        "max_tool_calls": 80,
        "max_tokens": 50000,
        "deadline_min": 45
      }
    }
  }
}
```

| Field | Purpose |
|---|---|
| `locked_paths` | Project-relative posix paths that the PreToolUse `autopilot-write-guard.py` hook hard-blocks on Write/Edit. Entries ending with `/` are prefix matches. **Always enforced** — even when no autopilot session is running. |
| `shared_workspaces` | Path prefixes (each ending with `/`) where worker subagents may write outside their per-worker sandbox. Useful for letting workers share an audit-output directory. |
| `task_kinds` | Per-task-kind overrides for the dispatched specialist subagent name, prompt template, and constraint caps. Defaults dispatch to `memex-planner`. |

The block is optional. With no `autopilot` block, the plugin's hook
scripts no-op when the state store is absent, and the schema is
forward-compatible.

## Specialist subagents

The autopilot ships **no** specialist agents — projects supply their
own. The defaults dispatch to Memex's built-in `memex-planner`
subagent (a generic investigation specialist).

To add a custom specialist, drop a definition into your project's
`.claude/agents/<name>.md` (or your own plugin's agents folder) and
point at it via `autopilot.task_kinds.<kind>.specialist` in
`memex.config.json`.

The worker contract that every specialist must satisfy is documented
at [`docs/autopilot/worker-contract.md`](autopilot/worker-contract.md).

## Environment variables

The hooks and helpers read these env vars (set by the coordinator
during DISPATCH; do not set them yourself in human sessions):

| Variable | Set by | Read by |
|---|---|---|
| `MEMEX_AUTOPILOT_ROLE` | coordinator (`worker` for spawned workers) | `autopilot-write-guard.py` |
| `MEMEX_AUTOPILOT_RUN_ID` | coordinator | `autopilot-write-guard.py`, `autopilot-subagent-stop.py`, `autopilot-notify.py`, `autopilot_worker.py` |
| `MEMEX_AUTOPILOT_WORKER_ID` | coordinator | same as above |
| `CLAUDE_PROJECT_DIR` | Claude Code | every script |

## Slash commands

| Command | Purpose |
|---|---|
| `/memex:autopilot-install` | Scaffold `.memex/.autopilot/` + `.memex/.inbox/`; verify prerequisites; optionally register cron tasks. |
| `/memex:autopilot-tick` | Fire one coordinator tick. The default if you wire the autopilot to a cron schedule. |
| `/memex:autopilot-status` | Print last tick, in-flight workers, inbox count, paused/rate-limited flags, budget. |
| `/memex:autopilot-pause` | Touch `.memex/.autopilot/PAUSED` (kill switch). Subsequent ticks no-op. |
| `/memex:autopilot-resume` | Remove the PAUSED file. |
| `/memex:autopilot-uninstall` | Archive the state store; deregister cron tasks. Hooks remain (no-op without state). |

## Hooks

The autopilot adds three plugin-level hooks (registered in
`hooks/hooks.json`):

| Event | Script | Behaviour |
|---|---|---|
| **PreToolUse** (Write/Edit) | `autopilot-write-guard.py` | Hard-blocks writes to `autopilot.locked_paths`; confines worker sessions to their sandbox + `autopilot.shared_workspaces`. |
| **SubagentStop** | `autopilot-subagent-stop.py` | Writes a `.done` marker into the worker's run-dir on subagent termination. |
| **Notification** | `autopilot-notify.py` | Forwards Claude Code's own Notification events into `.memex/.autopilot/alerts.jsonl`. |

All three early-exit when `.memex/.autopilot/` is absent (autopilot
not installed) so the rest of memex remains unaffected.

## Limitations / not in scope

- The plugin does **not** ship specialist subagents. Bring your own
  (or rely on the `memex-planner` default).
- Auto-commit is **not** implemented — every worker output lands in
  `.memex/.inbox/` for human review. There is no auto-commit safe
  lane today.
- Cron registration via `/memex:autopilot-install --with-cron`
  requires the `mcp__scheduled-tasks` MCP server. If absent, register
  cron via your OS / CI of choice.
- The `state.json` schema is at version 1. Bumping it is a
  coordinated change across the helper module, every tick phase, and
  every existing `state.json` in the wild — see the schema doc for
  the migration plan.

## See also

- [`autopilot/state-store-schema.md`](autopilot/state-store-schema.md) — on-disk layout
- [`autopilot/worker-contract.md`](autopilot/worker-contract.md) — worker prompt template + STATUS contract
- [`hook-catalog.md`](hook-catalog.md) — every memex hook (autopilot's three are listed)
- [`profile-authoring.md`](profile-authoring.md) — how to scaffold a project for memex
