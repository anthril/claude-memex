---
description: Run one Memex Autopilot coordinator tick — perceive backlog, plan, dispatch workers, gather, integrate
argument-hint: "[--dry-run] [--maintenance]"
allowed-tools: Read, Glob, Grep, Bash, Write, Agent
---

# /memex:autopilot-tick

Run one coordinator tick of the Memex Autopilot. Reads backlog signals (open questions, project-owner actions), picks the highest-value 1-3 actions, dispatches specialist subagents in worktrees, gathers their outputs, and routes everything to `.memex/.inbox/` for human review. **Nothing the tick does ever lands on `main` autonomously.**

## Usage

```
/memex:autopilot-tick                # full live tick
/memex:autopilot-tick --dry-run      # PERCEIVE + PLAN only; no dispatch
/memex:autopilot-tick --maintenance  # nightly maintenance variant
```

## State machine — 6 phases per tick

| Phase | What happens | Implementation |
|---|---|---|
| **PERCEIVE** | Snapshot backlog signals: OQs, owner-actions, git diff since last tick, inbox count | `tick_perceive.py` (deterministic) |
| **PLAN** | Score each backlog item; pick top-K (default 3 read-only specialists) | `tick_plan.py` (deterministic) |
| **DISPATCH** | Spawn N background workers in worktrees, one per task; embed full task.json in each prompt | This command, via the `Agent` tool |
| **GATHER** | For each Agent return value: hoist specialist artifact, synth REPORT.md + `.done` via `coordinator_synth_report.py` | This command + `coordinator_synth_report.py` |
| **INTEGRATE** | Validate REPORT.md STATUS lines; route artifacts to `.memex/.inbox/` or quarantine | `tick_integrate.py` (deterministic) |
| **LEARN** | Update heuristics in state.json; append `tick_complete` to history.jsonl | `tick_learn.py` (deterministic) |

## Behaviour

Numbered steps; execute strictly in order. Never skip a phase.

1. **Pre-flight checks.** Run:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/tick_preflight.py"
   ```
   Aborts the tick (exit 0) if paused, rate-limited, budget exhausted, or schema mismatch.

2. **Generate run-id.** `RUN_ID = $(date -u +'%Y-%m-%dT%H-%M-%SZ')`. Create `.memex/.autopilot/runs/$RUN_ID/`.

3. **PERCEIVE phase.**
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/tick_perceive.py" --run-id $RUN_ID --maintenance=<true|false>
   ```
   Writes `runs/$RUN_ID/perceive.json` with `oqs[]`, `owner_actions[]`, `commits_since_last_tick`, `inbox_count`, `resolved_oq_count`.

4. **PLAN phase.**
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/tick_plan.py" --run-id $RUN_ID
   ```
   Reads `perceive.json` plus `state.json:heuristics` and `memex.config.json#/autopilot/task_kinds`. Picks top-3 (or fewer if `max_workers_per_tick` smaller). For each pick, writes `runs/$RUN_ID/<worker-id>/task.json` per the worker contract. Also writes `plan.json` with the scoring trace.

5. **`--dry-run` short-circuit.** If `--dry-run` was passed in `$ARGUMENTS`, skip steps 6-9 and jump to step 10 with `dispatched=0`.

6. **DISPATCH phase.** Read each `task.json`. For each one, spawn a background worker via the `Agent` tool with:
   - `description`: short title from task.kind + task.target
   - `subagent_type`: the specialist name from `task.json.specialist` (defaults to `memex-planner` unless overridden in `memex.config.json`).
   - `isolation`: `worktree`
   - `run_in_background`: true
   - `prompt`: The **worker system prompt template** from [`docs/autopilot/worker-contract.md`](../docs/autopilot/worker-contract.md), with placeholders filled. **Embed the full task.json content as a fenced JSON block in the prompt** — worktrees branch from `HEAD` so the on-disk task.json is invisible inside the worker's worktree. Tell the worker its terminal message must end with a `STATUS: ok | failed | needs-input` line and must include a `Specialist output path: <abs path>` line.

   Append a `dispatched` line to `history.jsonl` for each worker.

7. **GATHER phase.** Background-agent completion notifications arrive automatically; do not poll. For each completed Agent:

   1. Capture the Agent's `result` (the worker's terminal text).
   2. Read the `worktreePath` from the notification.
   3. **Hoist the specialist artifact**: parse the `Specialist output path:` line from the worker's terminal text; if it is inside the worktree, copy it back to the same relative path on main. Use `Bash` with `mkdir -p` + `cp`.
   4. Save the worker's terminal text to a temp file (e.g. `.memex/.autopilot/runs/$RUN_ID/<worker-id>/.terminal.txt`) so multi-paragraph text isn't shell-escaped.
   5. **Synthesise REPORT.md + `.done`**:
      ```bash
      python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/coordinator_synth_report.py" \
        --run-id $RUN_ID \
        --worker-id <worker-id> \
        --terminal-message .memex/.autopilot/runs/$RUN_ID/<worker-id>/.terminal.txt \
        --specialist-output-path "<absolute path hoisted in step 3>" \
        --tokens <Agent.usage.total_tokens> \
        --tool-calls <Agent.usage.tool_uses> \
        --status-fallback
      ```

   Hard deadline: `state.json:config.tick_deadline_min` (default 45 min). Workers still in flight at deadline get a synthetic `STATUS: failed` REPORT.md.

8. **INTEGRATE phase.**
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/tick_integrate.py" --run-id $RUN_ID
   ```
   For each `runs/$RUN_ID/<worker-id>/REPORT.md`:
   - Parse the STATUS line.
   - Route per artifact class to `.memex/.inbox/$RUN_ID/` (drafts) or `.memex/.inbox/quarantine/`.
   - Append `gathered` line per worker, then `integrated` line per artifact, to `history.jsonl`.

9. **LEARN phase.**
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/tick_learn.py" --run-id $RUN_ID
   ```
   Updates `state.json`: increment `tick_count`; set `last_tick_at` and `next_tick_eta`; update `heuristics.task_kind_success_rate`; bump `heuristics.exponential_backoff` for failed tasks; append `tick_complete` to `history.jsonl`.

10. **Render summary.** Print one block:

    ```
    ## Memex Autopilot — tick <RUN_ID>
    - PERCEIVE: <N> active OQs, <O> owner-actions, <K> commits since last tick
    - PLAN: <P> tasks selected, <Q> deferred (backoff/quarantine)
    - DISPATCH: <D> workers spawned (or 0 — dry-run)
    - GATHER: <G> ok, <F> failed, <NI> needs-input
    - INTEGRATE: <I_inbox> inbox items, <I_auto> auto-committed
    - LEARN: state checkpointed, next tick eta <ETA>
    ```

    Decrement budget by `1 + dispatched` (1 for the coordinator session + 1 per worker).

## Default task kinds

| Task kind | Default specialist | Inbox lane |
|---|---|---|
| `oq-investigate` | `memex-planner` | `.memex/.inbox/$RUN_ID/oq-resolution-<slug>.md` |
| `owner-action-triage` | `memex-planner` | `.memex/.inbox/$RUN_ID/owner-action-triage-<slug>.md` |

Override the defaults in `memex.config.json#/autopilot/task_kinds`.

## Failure modes

- **Pre-flight rejects** → exit 0 with reason. (Paused, rate-limited, schema mismatch are all "success" of a no-op.)
- **PERCEIVE/PLAN crash** → no state mutation; abort and emit a quarantine note; the next tick can re-attempt.
- **DISPATCH spawn fails** → mark that task as failed; continue with other workers.
- **GATHER deadline** → synthetic STATUS: failed for non-completers; INTEGRATE proceeds.
- **INTEGRATE invalid REPORT** → route to `.memex/.inbox/quarantine/`; do NOT auto-commit.
- **LEARN crash** → state.json may be inconsistent; the next tick's pre-flight will detect and pause.

## See also

- `/memex:autopilot-install` — bootstrap before first tick
- `/memex:autopilot-status` — read state.json + history.jsonl tail
- `/memex:autopilot-pause` / `resume` — kill switch
- [`docs/autopilot/state-store-schema.md`](../docs/autopilot/state-store-schema.md) — on-disk layout
- [`docs/autopilot/worker-contract.md`](../docs/autopilot/worker-contract.md) — worker prompt template
