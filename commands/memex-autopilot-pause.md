---
description: Pause the Memex Autopilot — touches the PAUSED kill-switch file
argument-hint: "[reason]"
allowed-tools: Bash, Read
---

# /memex:autopilot-pause

Pause the Memex Autopilot loop. Creates `.memex/.autopilot/PAUSED`; the next coordinator tick reads this file in its pre-flight check and exits early as a no-op.

## Usage

```
/memex:autopilot-pause                 # pause; reason "manual"
/memex:autopilot-pause "release week"  # pause with a reason
```

## Behaviour

1. Verify autopilot is installed: `.memex/.autopilot/state.json` exists. If not, print `Autopilot not installed` and exit.

2. If `.memex/.autopilot/PAUSED` already exists, print its first line and exit (idempotent).

3. Otherwise write a single-line PAUSED file. Format: `<ISO8601 UTC> | reason: <reason or "manual">`.

4. Print confirmation:
   ```
   Memex Autopilot PAUSED at <timestamp>.
   Reason: <reason>
   The next tick (cron heartbeat) will see this file and exit cleanly.
   To resume: /memex:autopilot-resume
   ```

5. Append a `paused` line to `.memex/.autopilot/history.jsonl`.

## Implementation

Run the helper:
```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/lifecycle.py" pause --reason "$ARGUMENTS"
```

## See also

- `/memex:autopilot-resume` — un-pause
- `/memex:autopilot-status` — check current loop state
- `/memex:autopilot-install` — install or reinstall
