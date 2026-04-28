---
description: Print current Memex Autopilot state — last tick, in-flight workers, inbox count, paused/rate-limited flags
argument-hint: "[--verbose]"
allowed-tools: Bash, Read
---

# /memex:autopilot-status

Print the current Memex Autopilot state in a compact block.

## Usage

```
/memex:autopilot-status            # one-block summary
/memex:autopilot-status --verbose  # also print full state.json + last 5 history.jsonl entries
```

## Behaviour

1. If `.memex/.autopilot/state.json` does not exist, print `Autopilot not installed. Run /memex:autopilot-install.` and exit.

2. Read `state.json`, `BUDGET`, `PAUSED` flag, `RATE-LIMITED` flag.

3. Render one block:
   ```
   ## Memex Autopilot status
   - schema_version: 1
   - tick_count: <N>
   - last_tick_at: <ISO8601 + relative-time> (or "never")
   - next_tick_eta: <ISO8601 + relative-time> (or "n/a")
   - in_flight workers: <N> (top 3 listed, kind+target+started)
   - inbox awaiting review: <N> (top 3 oldest listed, with relative-time)
   - quarantined tasks: <N>
   - PAUSED: <yes / no with reason>
   - RATE-LIMITED: <yes / no>
   - budget remaining today: <N> sessions
   - heuristics: <success_rate per task_kind>
   ```

4. If `--verbose`, append:
   - Full pretty-printed `state.json`
   - Last 5 entries from `history.jsonl` (most recent first)

## Implementation

Run the helper:
```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/lifecycle.py" status $ARGUMENTS
```

## See also

- `/memex:autopilot-tick` — fire one tick manually
- `/memex:autopilot-pause` / `resume` — kill switch
- `/memex:autopilot-install` — bootstrap
