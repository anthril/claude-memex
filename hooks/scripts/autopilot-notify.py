#!/usr/bin/env python3
"""Notification hook for Memex Autopilot.

Forwards Claude Code's own ``Notification`` events (waiting-for-input
prompts, idle warnings, etc.) into a persisted alert queue so the
human sees them on next session start instead of discovering a
stalled tick hours later.

Behaviour:
  * Reads Notification JSON payload from stdin.
  * Appends one record to ``.memex/.autopilot/alerts.jsonl``
    containing ts, kind, message, session_id, and (when present)
    MEMEX_AUTOPILOT_RUN_ID / MEMEX_AUTOPILOT_WORKER_ID env vars.
  * Bumps ``state.json:notification_count`` (best-effort).
  * Stdlib only. Fail-open: any error → exit 0 with stderr WARN.
  * No-op if ``.memex/.autopilot/`` does not exist (autopilot
    not installed) — the hook fires for human sessions too, and
    we don't want to scaffold loop state outside the install command.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOOP_DIR = ".memex/.autopilot"


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def bump_notification_count(root: Path) -> None:
    """Best-effort: increment state.json:notification_count via autopilot_state."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "_lib"))
        try:
            import autopilot_state  # type: ignore
            state = autopilot_state.load_state()
            state["notification_count"] = int(state.get("notification_count") or 0) + 1
            autopilot_state.save_state_atomic(state)
        except Exception:
            pass
    except Exception:
        pass


def main() -> int:
    try:
        root = project_root()
        loop_root = root / LOOP_DIR
        if not loop_root.is_dir():
            return 0

        payload = read_stdin_json()
        record = {
            "ts": utcnow_iso(),
            "kind": "claude-notification",
            "session_id": str(payload.get("session_id") or payload.get("sessionId") or ""),
            "message": str(payload.get("message") or payload.get("title") or ""),
            "raw": payload,
        }
        run_id = os.environ.get("MEMEX_AUTOPILOT_RUN_ID", "").strip()
        worker_id = os.environ.get("MEMEX_AUTOPILOT_WORKER_ID", "").strip()
        if run_id:
            record["run_id"] = run_id
        if worker_id:
            record["worker_id"] = worker_id

        alerts_path = loop_root / "alerts.jsonl"
        with open(alerts_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

        bump_notification_count(root)
        return 0
    except Exception as exc:
        sys.stderr.write(f"[autopilot-notify] WARN: hook bypassed ({exc!r})\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
