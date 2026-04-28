"""Worker-side helpers for Memex Autopilot.

Workers spawned by the coordinator import this module to read their
task contract and write their REPORT.md without hand-rolling the
filesystem layout or the STATUS line format.

The PreToolUse write-guard hook (``autopilot-write-guard.py``) is the
authoritative enforcement layer — this module is a sanity net so
worker code reads cleanly and the contract is centralised.

Stdlib only. Python 3.10+. Side-effect-free on import.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

VALID_STATUSES: frozenset[str] = frozenset({"ok", "failed", "needs-input"})

WORKER_ALLOWED_PREFIXES: tuple[str, ...] = (
    ".memex/.autopilot/runs/",
)


class WorkerContractError(RuntimeError):
    """Raised when the worker's input contract is broken (missing env, malformed task.json)."""


def _project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def _ids() -> tuple[str, str]:
    run_id = os.environ.get("MEMEX_AUTOPILOT_RUN_ID", "").strip()
    worker_id = os.environ.get("MEMEX_AUTOPILOT_WORKER_ID", "").strip()
    if not run_id or not worker_id:
        raise WorkerContractError(
            "MEMEX_AUTOPILOT_RUN_ID and MEMEX_AUTOPILOT_WORKER_ID must be set for worker sessions"
        )
    return run_id, worker_id


def worker_dir() -> Path:
    run_id, worker_id = _ids()
    return _project_root() / ".memex" / ".autopilot" / "runs" / run_id / worker_id


def task_path() -> Path:
    return worker_dir() / "task.json"


def report_path() -> Path:
    return worker_dir() / "REPORT.md"


def read_task() -> dict[str, Any]:
    """Read the worker's task.json. Raises WorkerContractError on any problem."""
    path = task_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WorkerContractError(f"task.json missing at {path}") from exc
    try:
        data = json.loads(text)
    except Exception as exc:
        raise WorkerContractError(f"task.json malformed at {path}: {exc!r}") from exc
    if not isinstance(data, dict):
        raise WorkerContractError(f"task.json at {path} did not parse as a JSON object")
    for required in ("kind", "target", "runid", "worker_id", "specialist"):
        if required not in data:
            raise WorkerContractError(f"task.json missing required field: {required}")
    return data


def write_report(body: str, status: str) -> Path:
    """Write REPORT.md with a guaranteed valid trailing STATUS line.

    ``body`` is appended (trimmed) followed by a blank line and the
    STATUS line. If ``body`` already ends with a STATUS line we strip
    it and replace with the supplied ``status``.
    """
    if status not in VALID_STATUSES:
        raise WorkerContractError(
            f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}"
        )
    path = report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = (body or "").rstrip()
    lines = cleaned.splitlines()
    while lines and lines[-1].strip().startswith("STATUS:"):
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    final = "\n".join(lines)
    if final:
        final += "\n\n"
    final += f"STATUS: {status}\n"
    path.write_text(final, encoding="utf-8")
    return path


def validate_status_line(text: str) -> bool:
    """True if the last non-blank line of ``text`` is a recognised STATUS line."""
    if not text:
        return False
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("STATUS: "):
            value = stripped[len("STATUS: "):].strip()
            return value in VALID_STATUSES
        return False
    return False


def is_path_allowed_for_worker(rel_posix: str) -> bool:
    """Mirror of the write-guard's allowlist. Workers SHOULD self-check before Write/Edit."""
    if any(rel_posix.startswith(p) for p in WORKER_ALLOWED_PREFIXES):
        return True
    return False
