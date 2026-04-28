---
description: Resume the Memex Autopilot — removes the PAUSED kill-switch file
argument-hint: ""
allowed-tools: Bash, Read
---

# /memex:autopilot-resume

Un-pause the Memex Autopilot loop. Removes `.memex/.autopilot/PAUSED`; the next coordinator tick will proceed normally.

## Usage

```
/memex:autopilot-resume
```

## Behaviour

1. Verify autopilot is installed: `.memex/.autopilot/state.json` exists. If not, print `Autopilot not installed` and exit.

2. If `.memex/.autopilot/PAUSED` is absent, print `Already running (no PAUSED file)` and exit (idempotent).

3. Otherwise capture the PAUSED file's first-line content (timestamp + reason), then delete the file.

4. Append a `resumed` line to `.memex/.autopilot/history.jsonl` with the captured original-pause-reason.

5. Print confirmation:
   ```
   Memex Autopilot RESUMED.
   Was paused at <timestamp> for reason: <original reason>
   Next tick will proceed (next cron heartbeat).
   ```

## Implementation

Run the helper:
```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/lifecycle.py" resume
```

## See also

- `/memex:autopilot-pause` — pause again
- `/memex:autopilot-status` — check current loop state
- `/memex:autopilot-tick` — fire one tick manually (verify resume worked)
