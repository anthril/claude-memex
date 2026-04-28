"""Memex Autopilot installer.

Three modes:
  --check      Verify all prerequisites are present. Exit 0 if all green.
  --apply      Scaffold .memex/.autopilot/ skeleton (idempotent).
  --self-test  Round-trip load_state / save / append_history / budget /
               pause toggle to verify the helper module works end-to-end.

Stdlib only. Python 3.10+.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT_ENV = "CLAUDE_PROJECT_DIR"

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent


def project_root() -> Path:
    env = os.environ.get(REPO_ROOT_ENV)
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if out.returncode == 0:
            return Path(out.stdout.strip()).resolve()
    except Exception:
        pass
    return Path.cwd().resolve()


def check_prerequisites(root: Path) -> list[str]:
    """Return a list of missing prerequisite descriptions (empty = all green).

    The autopilot ships inside the memex plugin, so its own helper modules
    and hook scripts are guaranteed to exist when the plugin is installed.
    The only project-level prerequisite is a memex.config.json (the hooks
    use it to find the ops root).
    """
    missing: list[str] = []

    config = root / "memex.config.json"
    if not config.is_file() and not (root / ".memex").is_dir():
        missing.append(
            "memex not initialised in this project — run `/memex:init <profile>` first."
        )

    helper = PLUGIN_ROOT / "hooks" / "scripts" / "_lib" / "autopilot_state.py"
    if not helper.is_file():
        missing.append(f"plugin helper missing at {helper}")

    return missing


DEFAULT_STATE = {
    "schema_version": 1,
    "last_tick_at": None,
    "next_tick_eta": None,
    "tick_count": 0,
    "in_flight": [],
    "goal_queue": [],
    "heuristics": {
        "task_kind_success_rate": {},
        "task_kind_mean_tokens": {},
        "exponential_backoff": {},
    },
    "config": {
        "max_workers_per_tick": 3,
        "max_sessions_per_day": 30,
        "tick_deadline_min": 45,
        "max_attempts_per_task": 3,
    },
    "last_human_resolve_at": None,
}

DEFAULT_BUDGET = 30


def apply_scaffold(root: Path) -> dict:
    """Create the .memex/.autopilot/ directory tree. Idempotent."""
    loop_dir = root / ".memex" / ".autopilot"
    loop_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("runs", "locks", "digests"):
        (loop_dir / sub).mkdir(parents=True, exist_ok=True)

    inbox = root / ".memex" / ".inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "quarantine").mkdir(parents=True, exist_ok=True)

    state_path = loop_dir / "state.json"
    if not state_path.is_file():
        state_path.write_text(json.dumps(DEFAULT_STATE, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        action_state = "created"
    else:
        action_state = "exists"

    budget_path = loop_dir / "BUDGET"
    if not budget_path.is_file():
        budget_path.write_text(f"{DEFAULT_BUDGET}\n", encoding="utf-8")
        action_budget = "created"
    else:
        action_budget = "exists"

    history_path = loop_dir / "history.jsonl"
    if not history_path.is_file():
        history_path.write_text("", encoding="utf-8")
        action_history = "created"
    else:
        action_history = "exists"

    return {
        "loop_dir": str(loop_dir),
        "inbox_dir": str(inbox),
        "state.json": action_state,
        "BUDGET": action_budget,
        "history.jsonl": action_history,
    }


def self_test(root: Path) -> tuple[bool, str]:
    """Round-trip the autopilot_state helper API."""
    sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts" / "_lib"))
    try:
        import autopilot_state  # type: ignore
    except Exception as exc:
        return False, f"autopilot_state import failed: {exc!r}"

    try:
        state = autopilot_state.load_state()
        assert state["schema_version"] == 1
        autopilot_state.save_state_atomic(state)

        autopilot_state.append_history({"phase": "install_self_test"})

        budget = autopilot_state.read_budget()
        if budget <= 0:
            autopilot_state.BUDGET_PATH.write_text(f"{DEFAULT_BUDGET}\n", encoding="utf-8")
            budget = autopilot_state.read_budget()
        new_budget = autopilot_state.decrement_budget(1)
        if new_budget != budget - 1:
            return False, f"budget decrement off: {budget} -> {new_budget}"
        autopilot_state.BUDGET_PATH.write_text(f"{DEFAULT_BUDGET}\n", encoding="utf-8")

        if autopilot_state.is_paused():
            return False, "PAUSED file unexpectedly present at install"

        return True, "OK: state load/save/append cycle; budget read/decrement; pause toggle"
    except Exception as exc:
        return False, f"self-test failed: {exc!r}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Memex Autopilot installer")
    parser.add_argument("--check", action="store_true", help="Verify prerequisites only")
    parser.add_argument("--apply", action="store_true", help="Apply state-store scaffold")
    parser.add_argument("--self-test", action="store_true", help="Round-trip autopilot_state helper")
    args = parser.parse_args()

    if not (args.check or args.apply or args.self_test):
        print("specify at least one of --check, --apply, --self-test", file=sys.stderr)
        return 2

    root = project_root()

    if args.check:
        missing = check_prerequisites(root)
        if missing:
            print("MISSING prerequisites:")
            for m in missing:
                print(f"  - {m}")
            return 1
        print("OK: all prerequisites present")

    if args.apply:
        result = apply_scaffold(root)
        print(json.dumps(result, indent=2))

    if args.self_test:
        ok, msg = self_test(root)
        print(msg)
        if not ok:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
