---
description: Uninstall the Memex Autopilot — deregister cron tasks, archive state
argument-hint: "[--keep-state]"
allowed-tools: Bash, Read
---

# /memex:autopilot-uninstall

Uninstall the Memex Autopilot. Deregisters scheduled-tasks cron entries (if registered). Archives the state store rather than deleting it (so a re-install can resume).

## Usage

```
/memex:autopilot-uninstall              # deregister cron, archive state
/memex:autopilot-uninstall --keep-state # deregister cron only; leave .memex/.autopilot/ untouched
```

## Behaviour

1. Verify autopilot is installed.

2. **Deregister cron**: read `.memex/.autopilot/scheduled-task-ids.json`. For each task ID, call `mcp__scheduled-tasks__update_scheduled_task` with `enabled: false` (preferred) or fall back to manual deletion if the user confirms. **Never silently delete cron tasks** — surface the IDs and ask the user.

3. **Pause first**: write the PAUSED flag with reason "uninstall in progress" so any in-flight tick stops cleanly.

4. **Archive state** (unless `--keep-state`): rename `.memex/.autopilot/` to `.memex/.autopilot.archived-<timestamp>/`. The user can `rm -rf` the archive when satisfied.

5. **Hooks remain**. The PreToolUse / SubagentStop / Notification hooks stay registered in the memex plugin's `hooks.json`. They no-op when `.memex/.autopilot/` is absent (verified by their fail-open paths). To fully remove them, uninstall the memex plugin or pin a pre-autopilot version.

6. Print summary:
   ```
   Memex Autopilot uninstalled.
   - Cron: <N> tasks deregistered, <M> retained (action by user).
   - State: archived at .memex/.autopilot.archived-<timestamp>/
   - Hooks: still loaded by the memex plugin (no-op without state).

   To reinstall: /memex:autopilot-install
   ```

## Failure modes

- MCP scheduled-tasks tool unavailable → list the task IDs from the JSON file and instruct the user to deregister manually.
- State directory missing → already uninstalled; print and exit.
- `--keep-state` with active in-flight workers → warn but proceed (state preserved; workers will see PAUSED on next tick).

## Implementation

Run the helper:
```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot/lifecycle.py" uninstall $ARGUMENTS
```

## See also

- `/memex:autopilot-install` — reinstall
- `/memex:autopilot-pause` / `resume` — temporary halt without uninstalling
