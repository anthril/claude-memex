# Memex Autopilot — state store schema

Authoritative spec for the on-disk layout of `.memex/.autopilot/`.
The runtime helpers live at [`hooks/scripts/_lib/autopilot_state.py`](../../hooks/scripts/_lib/autopilot_state.py);
the `/memex:autopilot-install` command creates these files; this doc is
what each producer/consumer must agree on.

The whole `.memex/.autopilot/` tree is ephemeral runtime state — never
source. Spawned worker reports also live here, namespaced per-run.

## Top-level layout

```
.memex/.autopilot/
├── state.json                  # current goal queue, in-flight, heuristics, schema_version
├── PAUSED                      # kill switch (presence = halt)
├── RATE-LIMITED                # rate-limit signal (presence = back off; coordinator triples next-tick gap)
├── BUDGET                      # plain-text integer; remaining sessions today
├── runs/<run-id>/              # one directory per coordinator tick (ISO8601 timestamp run-id)
│   ├── perceive.json           # backlog snapshot
│   ├── plan.json               # chosen tasks + scoring trace
│   ├── SUMMARY.md              # tick summary (human-readable)
│   ├── tick.log                # phase transitions + timestamps
│   └── <worker-id>/            # one directory per worker (per task this tick)
│       ├── task.json           # the worker's contract (set by coordinator)
│       ├── REPORT.md           # the worker's output (last line: STATUS: ok|failed|needs-input)
│       ├── .done               # marker file written by SubagentStop hook on completion
│       └── transcript.jsonl    # worker's tool calls (for replay)
├── locks/                      # finite-TTL file locks; <resource>.lock JSON
├── digests/<YYYY-WW>.md        # weekly digest of past 7 days' ticks
├── alerts.jsonl                # Notification-hook alert queue
└── history.jsonl               # append-only ledger; every phase transition gets one line
```

The autopilot uses Memex's existing `.memex/.inbox/` directory as the
human-review surface for routed worker artifacts. That directory is
shared with the rest of Memex and is not autopilot-private.

## `state.json` schema (schema_version = 1)

```json
{
  "schema_version": 1,
  "last_tick_at": "2026-04-27T14:30:00Z",
  "next_tick_eta": "2026-04-27T16:00:00Z",
  "tick_count": 142,
  "in_flight": [
    {
      "worker_id": "w-abc",
      "task_kind": "oq-investigate",
      "target": "active-perception-info-gain-estimator",
      "started_at": "2026-04-27T14:30:05Z",
      "worktree": "agent-aXXX"
    }
  ],
  "goal_queue": [
    {
      "kind": "oq-investigate",
      "target": "...",
      "priority": 0.92,
      "blocked_by": null,
      "attempts": 0
    }
  ],
  "heuristics": {
    "task_kind_success_rate": {"oq-investigate": 0.88, "owner-action-triage": 0.95},
    "task_kind_mean_tokens": {"oq-investigate": 18000, "owner-action-triage": 6000},
    "exponential_backoff": {
      "oq-investigate:replication-partners": {"failures": 2, "next_eligible_at": "2026-04-28T08:00:00Z"}
    }
  },
  "config": {
    "max_workers_per_tick": 3,
    "max_sessions_per_day": 30,
    "tick_deadline_min": 45,
    "max_attempts_per_task": 3
  },
  "last_human_resolve_at": "2026-04-26T22:00:00Z",
  "last_modified_at": "2026-04-27T14:30:00Z"
}
```

`schema_version` MUST be checked by every reader. Mismatched versions
indicate a coordinator/worker drift; the reading session should pause
the loop and surface a diagnostic to `.memex/.inbox/`.

`last_modified_at` is set by `autopilot_state.save_state_atomic` on
every write; never set by callers.

## `history.jsonl` schema

One JSON object per line. Keys vary by phase but always include
`ts` (ISO8601 UTC) and `phase`. Examples:

```jsonl
{"ts": "2026-04-27T14:30:00Z", "phase": "tick_start", "run_id": "2026-04-27T14-30-00", "tick_count": 142}
{"ts": "2026-04-27T14:30:12Z", "phase": "perceive", "run_id": "...", "active_oqs": 14, "high_due": 0}
{"ts": "2026-04-27T14:30:30Z", "phase": "dispatched", "run_id": "...", "worker_id": "w-001", "kind": "oq-investigate", "target": "replication-partners"}
{"ts": "2026-04-27T14:42:11Z", "phase": "gathered", "run_id": "...", "worker_id": "w-001", "status": "ok", "tokens_in": 18000, "tokens_out": 9500}
{"ts": "2026-04-27T14:42:30Z", "phase": "tick_complete", "run_id": "...", "inbox_added": 1, "auto_committed": 0}
```

History is append-only. Older entries never modified. Replayable.

## `BUDGET` file

Single line, plain integer. Updated by
`autopilot_state.decrement_budget()` and rewritten daily by
`autopilot-budget-reset.py`. Floored at 0.

## `PAUSED` / `RATE-LIMITED` files

Sentinel files. Their *presence* is the signal; content is ignored
(though convention is to write a one-line ISO8601 timestamp + reason).
Created by `/memex:autopilot-pause` or by the coordinator on
rate-limit detection. Removed by `/memex:autopilot-resume`.

## Per-worker `task.json`

Set by the coordinator before dispatch. Worker reads this first.

```json
{
  "kind": "oq-investigate",
  "target": "active-perception-info-gain-estimator",
  "runid": "2026-04-27T14-30-00",
  "worker_id": "w-abc",
  "specialist": "memex-planner",
  "constraints": {
    "max_tool_calls": 80,
    "max_tokens": 50000,
    "deadline_at": "2026-04-27T15:15:00Z"
  },
  "prompt_for_specialist": "Investigate the open question at .memex/.open-questions/active-perception-info-gain-estimator.md ..."
}
```

The `specialist` field names a Claude Code subagent. The autopilot
ships no specialist agents itself — host projects supply them
(or use Memex's existing `memex-ingestor` / `memex-linter` /
`memex-planner` subagents).

## Per-worker `REPORT.md`

Worker output. **Last line MUST be exactly** one of:

```
STATUS: ok
STATUS: failed
STATUS: needs-input
```

Coordinator's GATHER phase rejects any report missing this contract.

## Schema-version history

| Version | Date | Change |
|---|---|---|
| 1 | 2026-04-27 | Initial schema introduced for the autopilot MVP (originated in the AURORA project) |

When bumping `schema_version`, prefer additive changes. Removing or
renaming a field requires a migration step in the install command.

## Do NOT edit by hand outside `.memex/.inbox/`

Everything under `.memex/.autopilot/` is machine state. Editing
`state.json`, `history.jsonl`, or any `runs/<run-id>/` artifact by hand
will desynchronise the coordinator. Use `/memex:autopilot-pause`, then
the slash commands, then `/memex:autopilot-resume`.

`.memex/.inbox/` is the only safe lane for human input — that is its
purpose.
