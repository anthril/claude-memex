#!/usr/bin/env python3
"""SubagentStop hook for Memex Autopilot.

Fires when a background subagent (typically a worker spawned by the
coordinator's DISPATCH phase) terminates. Writes a deterministic
``.done`` marker into the worker's per-run sandbox so the
coordinator's GATHER phase has a fast filesystem-watchable signal —
no need to poll for ``REPORT.md`` content.

Behaviour:
  * Reads SubagentStop JSON payload from stdin (best-effort; not
    actually required to function — env vars are the canonical
    worker context).
  * Reads ``MEMEX_AUTOPILOT_RUN_ID`` and ``MEMEX_AUTOPILOT_WORKER_ID``
    from the environment. If either is missing, no-op (this is
    not a worker subagent).
  * Writes ``<run-dir>/<worker-id>/.done`` containing a short JSON
    blob: ``{"ts": "...", "session_id": "...", "stop_hook_input": ...}``.
  * Idempotent: writing the marker twice for the same worker is
    harmless (the file is small and overwriting is fine).
  * Optionally appends a one-line summary to history.jsonl when the
    autopilot_state helper module is importable.
  * Stdlib only. Fail-open: any error → exit 0 with a stderr WARN.
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


def append_history_safe(record: dict) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "_lib"))
        try:
            import autopilot_state  # type: ignore
            autopilot_state.append_history(record)
            return
        except Exception:
            pass
    except Exception:
        pass
    try:
        history_path = project_root() / ".memex" / ".autopilot" / "history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        record = dict(record)
        record.setdefault("ts", utcnow_iso())
        line = json.dumps(record, sort_keys=True)
        with open(history_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def main() -> int:
    try:
        run_id = os.environ.get("MEMEX_AUTOPILOT_RUN_ID", "").strip()
        worker_id = os.environ.get("MEMEX_AUTOPILOT_WORKER_ID", "").strip()
        if not run_id or not worker_id:
            return 0

        payload = read_stdin_json()
        session_id = payload.get("session_id") or payload.get("sessionId") or ""

        root = project_root()
        worker_dir = root / ".memex" / ".autopilot" / "runs" / run_id / worker_id
        worker_dir.mkdir(parents=True, exist_ok=True)

        marker = worker_dir / ".done"
        marker_data = {
            "ts": utcnow_iso(),
            "session_id": str(session_id),
            "run_id": run_id,
            "worker_id": worker_id,
        }
        marker.write_text(json.dumps(marker_data, sort_keys=True) + "\n", encoding="utf-8")

        append_history_safe({
            "phase": "subagent_stop",
            "run_id": run_id,
            "worker_id": worker_id,
            "session_id": str(session_id),
        })

        return 0
    except Exception as exc:
        sys.stderr.write(f"[autopilot-subagent-stop] WARN: hook bypassed ({exc!r})\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
