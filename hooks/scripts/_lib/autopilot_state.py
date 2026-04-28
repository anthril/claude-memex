"""Single source of truth for Memex Autopilot loop state.

Hooks and slash commands import this module to read or mutate the
loop's persistent state. The on-disk layout is documented in
``docs/autopilot/state-store-schema.md`` — that doc is authoritative;
this module is its runtime.

Design constraints:
  * Stdlib only. No third-party deps.
  * Atomic writes — temp-file + ``os.replace`` so a crash mid-write
    cannot leave a half-written ``state.json``.
  * Defensive reads — if ``state.json`` is missing or unparseable
    the loader returns the default schema rather than raising.
  * No side effects on import. Callers control when files are read or
    written; nothing is ensured-to-exist by simply importing.

The schema_version field guards format drift between coordinator and
worker sessions. Bump it when the on-disk layout changes; older
sessions reading a newer file should refuse to mutate (caller's job).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

LOOP_DIR_NAME = ".memex/.autopilot"
STATE_FILE = "state.json"
HISTORY_FILE = "history.jsonl"
BUDGET_FILE = "BUDGET"
PAUSED_FILE = "PAUSED"
RATE_LIMITED_FILE = "RATE-LIMITED"


def _project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
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
            top = out.stdout.strip()
            if top:
                return Path(top).resolve()
    except Exception:
        pass
    return Path.cwd().resolve()


def loop_dir() -> Path:
    return _project_root() / LOOP_DIR_NAME


STATE_PATH: Path = loop_dir() / STATE_FILE
HISTORY_PATH: Path = loop_dir() / HISTORY_FILE
BUDGET_PATH: Path = loop_dir() / BUDGET_FILE
PAUSED_PATH: Path = loop_dir() / PAUSED_FILE
RATE_LIMITED_PATH: Path = loop_dir() / RATE_LIMITED_FILE


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
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


def load_state() -> dict[str, Any]:
    """Return the current state dict; default schema on any read error."""
    path = STATE_PATH
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            return default_state()
        return data
    except FileNotFoundError:
        return default_state()
    except Exception:
        return default_state()


def save_state_atomic(state: dict[str, Any]) -> None:
    """Write state.json atomically: temp-file then os.replace."""
    state = dict(state)
    state["last_modified_at"] = _utcnow_iso()
    target = STATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{STATE_FILE}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except Exception:
            pass
        raise


def append_history(record: dict[str, Any]) -> None:
    """Append a single JSON line to history.jsonl. Adds ``ts`` if absent."""
    record = dict(record)
    record.setdefault("ts", _utcnow_iso())
    path = HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_budget() -> int:
    """Return remaining session budget; 0 on any read error or missing file."""
    try:
        text = BUDGET_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return 0
        return int(text.splitlines()[0])
    except FileNotFoundError:
        return 0
    except Exception:
        return 0


def decrement_budget(by: int = 1) -> int:
    """Subtract ``by`` from the budget; returns the new value (floored at 0)."""
    current = read_budget()
    new = max(0, current - by)
    BUDGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_PATH.write_text(f"{new}\n", encoding="utf-8")
    return new


def is_paused() -> bool:
    return PAUSED_PATH.exists()


def is_rate_limited() -> bool:
    return RATE_LIMITED_PATH.exists()
