# Memex Autopilot — worker contract

Authoritative spec for what every worker session does, must do, and
must not do. The coordinator's DISPATCH phase spawns workers via
`Agent(run_in_background=true, isolation="worktree")`; each worker is
a thin wrapper around a host-project specialist agent. The autopilot
ships no specialist agents of its own — projects supply them, or use
Memex's existing `memex-ingestor` / `memex-linter` / `memex-planner`
subagents.

The state-store schema in [state-store-schema.md](state-store-schema.md)
defines the on-disk artifacts; this doc defines the worker's runtime
contract.

## Worker system prompt template

Every worker is dispatched with the following preamble injected at
the top of its system prompt. The coordinator fills the placeholders
**and embeds the full task.json content inline** (the run-dir on
main's working tree is invisible inside the worker's worktree, since
worktrees branch from `HEAD`).

```
You are a worker for Memex Autopilot run <run-id>.
Worker id: <worker-id>
Worktree: <worktree-name> (you are already inside it; never EnterWorktree out)

Your task (canonical — task.json embedded; on-disk copy may be absent inside the worktree):
```json
<task.json content, pretty-printed>
```

You ARE the specialist agent named in task.specialist. Run your normal specialist workflow against the prompt in task.prompt_for_specialist. Write your findings to your normal bounded artifact root (the path your agent definition prescribes). Do NOT write a REPORT.md anywhere — the coordinator synthesises it from your terminal message.

Hard rules:
1. The task above is canonical. If you also see `.memex/.autopilot/runs/<run-id>/<worker-id>/task.json` on disk, treat the embedded blob as authoritative on conflict.
2. Invoke yourself as the specialist named in task.specialist; do not delegate to a sibling agent.
3. Write your specialist artifact to your normal bounded root only. Do NOT write inside `.memex/.autopilot/runs/`.
4. Your terminal message MUST end with a line that is exactly one of:
       STATUS: ok
       STATUS: failed
       STATUS: needs-input
   The coordinator parses this line; missing or malformed = quarantine.
5. Cite the absolute path to your specialist artifact in the terminal message under the heading `Specialist output path:`. The coordinator copies that artifact out of your worktree back to main.
6. Report tokens used and tool-call count if you have them, on lines beginning `Tokens used:` and `Tool calls made:`.
7. Never touch main directly. Never commit. Never run git push, git merge, or any destructive command.
8. Never spawn another agent. You are a leaf.
9. If the harness sets MEMEX_AUTOPILOT_ROLE / MEMEX_AUTOPILOT_RUN_ID / MEMEX_AUTOPILOT_WORKER_ID, leave them set — the PreToolUse write-guard hook reads them to enforce path bounds. Do not unset.
```

### Why the coordinator owns REPORT.md

Specialist agents typically carry their own write allow-lists scoped
to their normal output roots. Asking them to also write `REPORT.md`
under `.memex/.autopilot/runs/<runid>/<worker-id>/` violates their
own definitions and they refuse. Rather than weaken every specialist's
allow-list, the coordinator synthesises REPORT.md from the worker's
terminal message via
[`scripts/autopilot/coordinator_synth_report.py`](../../scripts/autopilot/coordinator_synth_report.py).
The worker's only contract obligation is the trailing `STATUS:` line.

## task.json schema

Set by the coordinator before dispatch. Worker reads this first; it is
the worker's only input contract.

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

| Field | Type | Description |
|---|---|---|
| `kind` | string | Task kind. Drives heuristics + history aggregation. Must match a key in `state.json:heuristics.task_kind_*`. |
| `target` | string | Free-form target identifier (OQ slug, file path, owner-action slug, etc.) |
| `runid` | string | Coordinator's run id. Must match the URL path. |
| `worker_id` | string | Coordinator-assigned worker id. Stable for retry sequences. |
| `specialist` | string | Name of the host-project subagent to invoke. |
| `constraints.max_tool_calls` | int | Soft cap; worker SHOULD self-monitor and emit `STATUS: needs-input` if exceeded. |
| `constraints.max_tokens` | int | Soft cap; same self-monitoring policy. |
| `constraints.deadline_at` | ISO8601 UTC | Hard deadline; if exceeded the Stop hook synthesizes `STATUS: failed`. |
| `prompt_for_specialist` | string | The full prompt the worker passes to the specialist agent. |

The schema is forward-compatible: workers SHOULD ignore unknown fields
rather than reject the task.

## REPORT.md template

REPORT.md is **synthesised by the coordinator**, not by the worker —
see "Why the coordinator owns REPORT.md" above. The worker's job is to
emit a clean terminal message ending with a `STATUS:` line; the
coordinator runs `coordinator_synth_report.py` to render the report
below from that message and to drop the `.done` marker.

The coordinator's helper expects the worker's terminal message to:

1. Have a final line that is exactly `STATUS: ok`, `STATUS: failed`,
   or `STATUS: needs-input`.
2. Include `Specialist output path: <absolute path>` somewhere in the
   message so the coordinator can hoist the artifact out of the
   worker's worktree back to main.
3. Optionally include `Tokens used: <int>` and `Tool calls made: <int>`
   for telemetry.

The synthesised REPORT.md follows this template; do NOT hand-write it
as a worker:

```markdown
# Worker report — <worker-id>

## Task
- kind: <task.kind>
- target: <task.target>
- runid: <task.runid>

## Specialist invoked
<task.specialist>

## Specialist output path
<absolute path to the specialist's actual report file>

## Specialist terminal message
<verbatim worker terminal text, with the trailing STATUS line stripped>

## Tokens used
<integer or n/a>

## Tool calls made
<integer or n/a>

## Notes
- REPORT.md synthesised by the coordinator (`coordinator_synth_report.py`) at <ts> from the worker's terminal message; specialists in worker mode write only to their bounded artifact roots, so REPORT.md authorship is the coordinator's job.

STATUS: ok
```

### STATUS line semantics

| Line | Meaning | Coordinator routing |
|---|---|---|
| `STATUS: ok` | Specialist ran, produced a useful artifact, no human attention required beyond the inbox lane it lands in | INTEGRATE per artifact-class lane (route to `.memex/.inbox/`) |
| `STATUS: failed` | Specialist errored, ran out of budget, or produced an invalid artifact | bump exponential backoff; re-queue if attempts < max_attempts_per_task |
| `STATUS: needs-input` | Specialist completed but flagged that human judgment is required | route artifact to `.memex/.inbox/<runid>/<slug>.md`, attach to `.memex/.inbox/INBOX.md` index |

## Worker helper module — `autopilot_worker.py`

Workers (and the coordinator's dispatch shim) import the helper at
[`hooks/scripts/_lib/autopilot_worker.py`](../../hooks/scripts/_lib/autopilot_worker.py)
to avoid hand-rolling task-reading and report-writing. The module is
stdlib-only and side-effect-free on import.

| Function | Purpose |
|---|---|
| `read_task() -> dict` | Reads `task.json` from the path implied by `MEMEX_AUTOPILOT_RUN_ID` + `MEMEX_AUTOPILOT_WORKER_ID`. Raises `WorkerContractError` if either env var is missing or the file is malformed. |
| `report_path() -> Path` | Returns the absolute path to the worker's `REPORT.md`. |
| `write_report(body: str, status: str) -> None` | Writes `REPORT.md` with the body, ensuring the last line is exactly `STATUS: <status>`. Appends a trailing newline. Raises if status is not one of `ok`/`failed`/`needs-input`. |
| `validate_status_line(text: str) -> bool` | True if the last non-blank line of `text` is a recognised STATUS line. |
| `is_path_allowed_for_worker(rel_posix: str) -> bool` | The path-prefix allowlist — same as the autopilot-write-guard hook. Workers SHOULD double-check writes against this before invoking Write/Edit tools. |

The helper is a sanity net, not a replacement for the PreToolUse
write-guard hook. The hook is the authoritative enforcement layer; the
helper exists so worker code reads cleanly.

## Hard rules — what workers MUST NOT do

1. **Never write outside the specialist's bounded artifact root.**
   That is your only writable area.
2. **Never write `REPORT.md` inside `.memex/.autopilot/runs/`.**
   REPORT.md is the coordinator's synthesis from your terminal message;
   trying to write it yourself will be denied by your own specialist
   agent's allow-list.
3. **Never spawn another agent.** Workers are leaves of the dispatch
   tree.
4. **Never `git commit`, `git push`, `git merge`, or `git reset`.**
   All commits are human-driven via the inbox lane.
5. **Never edit any path on the project's `autopilot.locked_paths`
   list** (configured in `memex.config.json`). The denylist is
   hard-blocked by `autopilot-write-guard.py` regardless of role.
6. **Never silently truncate the specialist's output.** If the artifact
   is too large, write what fits and emit `STATUS: needs-input` with a
   note explaining the truncation.
7. **Never omit the trailing `STATUS:` line from your terminal
   message.** Coordinator quarantines workers with no STATUS line.

## Soft rules — workers SHOULD

1. Self-monitor token + tool-call budget and emit `STATUS: needs-input`
   rather than blowing past a constraint.
2. Cite source paths (specialist's report path, OQ filename, etc.) in
   the terminal message so the coordinator's INTEGRATE phase has
   provenance.
3. Time-box specialist invocation: if it takes >
   `constraints.deadline_at`, abort with `STATUS: failed`.
4. Capture the specialist's terminal message (its last 1-2 paragraphs)
   verbatim so the coordinator's synthesised REPORT.md is useful.

## Coordinator-side guarantees workers can rely on

1. The worker's worktree was freshly created from `main`; nothing is
   dirty.
2. The full task.json content is embedded in the dispatch prompt
   (canonical). The on-disk task.json may also exist on main, but
   workers MUST trust the embedded copy on conflict — worktrees branch
   from `HEAD`, so files in the run-dir on main's working tree may be
   invisible inside the worktree.
3. `.memex/.autopilot/runs/<run-id>/<worker-id>/` exists and is
   writable on main.
4. The PreToolUse write-guard hook is registered and active. Denylist
   enforcement always fires; worker-sandbox enforcement fires only
   when `MEMEX_AUTOPILOT_ROLE=worker` is set in the worker's env.
5. The coordinator hoists the worker's specialist artifact (cited via
   `Specialist output path:` in the terminal message) from the
   worktree back to main after the Agent returns.
6. The coordinator runs `coordinator_synth_report.py` with the
   worker's terminal message + worker-id; the helper writes REPORT.md
   and the `.done` marker. Workers do NOT write either.
7. If the worker terminal message has no valid trailing STATUS line,
   the coordinator may fall back to `STATUS: needs-input` (with
   `--status-fallback`) or quarantine the worker.

## Cross-references

- [state-store-schema.md](state-store-schema.md) — on-disk artifact layout
- [`autopilot_state.py`](../../hooks/scripts/_lib/autopilot_state.py) — state-store helpers
- [`autopilot-write-guard.py`](../../hooks/scripts/autopilot-write-guard.py) — PreToolUse trust enforcer
- [`autopilot-subagent-stop.py`](../../hooks/scripts/autopilot-subagent-stop.py) — `.done` marker writer
- [`autopilot-notify.py`](../../hooks/scripts/autopilot-notify.py) — Notification forwarder

## Schema-version history

| Version | Date | Change |
|---|---|---|
| 1 | 2026-04-27 | Initial worker contract for the autopilot MVP (originated in the AURORA project) |
| 2 | 2026-04-27 | Coordinator owns REPORT.md (synthesised from worker terminal text); task.json embedded in dispatch prompt rather than read from worktree disk; SubagentStop dependency removed (coordinator writes `.done` via `coordinator_synth_report.py`). |
