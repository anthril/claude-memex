"""Pre-flight checks for a Memex Autopilot tick.

Verifies the loop is in a state to accept work:
  * State store present and parseable.
  * schema_version matches.
  * Not paused.
  * Not rate-limited (or rate-limit cooldown elapsed).
  * Budget > 0.

Exit 0 if green; prints "PROCEED". Exit 0 if blocked (paused, etc.) with
a reason — a paused tick is *success*, not failure. Exit 1 only on
genuine internal errors.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EXPECTED_SCHEMA = 1


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def main() -> int:
    root = project_root()
    loop_dir = root / ".memex" / ".autopilot"

    if not loop_dir.is_dir():
        print("BLOCKED: autopilot not installed (run /memex:autopilot-install)")
        return 0

    state_path = loop_dir / "state.json"
    if not state_path.is_file():
        print("BLOCKED: state.json missing")
        return 0

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: state.json malformed: {exc!r}")
        return 1

    schema = state.get("schema_version")
    if schema != EXPECTED_SCHEMA:
        print(f"BLOCKED: schema_version mismatch (got {schema!r}, expected {EXPECTED_SCHEMA})")
        return 0

    if (loop_dir / "PAUSED").exists():
        print("BLOCKED: PAUSED file present (run /memex:autopilot-resume)")
        return 0

    if (loop_dir / "RATE-LIMITED").exists():
        print("BLOCKED: RATE-LIMITED file present (waiting for cool-down)")
        return 0

    budget_path = loop_dir / "BUDGET"
    if budget_path.is_file():
        try:
            budget = int(budget_path.read_text(encoding="utf-8").strip().splitlines()[0])
        except Exception:
            budget = 0
        if budget <= 0:
            print(f"BLOCKED: BUDGET exhausted ({budget} sessions remaining)")
            return 0

    config = state.get("config") or {}
    max_workers = int(config.get("max_workers_per_tick", 3))

    print(f"PROCEED: schema={schema}, max_workers={max_workers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
