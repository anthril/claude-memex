#!/usr/bin/env python3
"""Daily budget-reset for Memex Autopilot.

Rewrites ``.memex/.autopilot/BUDGET`` to the configured
``max_sessions_per_day`` value. Designed to be invoked by a daily
cron (00:01) registered via the project's scheduling tool of choice
(e.g. ``mcp__scheduled-tasks__create_scheduled_task``, OS cron, or
GitHub Actions).

No-op if ``.memex/.autopilot/`` does not exist.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def main() -> int:
    root = project_root()
    loop_dir = root / ".memex" / ".autopilot"
    if not loop_dir.is_dir():
        print("autopilot not installed — nothing to reset")
        return 0
    state_path = loop_dir / "state.json"
    budget_path = loop_dir / "BUDGET"

    target = 30
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            target = int(state.get("config", {}).get("max_sessions_per_day", 30))
        except Exception:
            pass

    budget_path.parent.mkdir(parents=True, exist_ok=True)
    budget_path.write_text(f"{target}\n", encoding="utf-8")
    print(f"BUDGET reset to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
