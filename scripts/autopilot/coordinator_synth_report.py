"""Coordinator-side helper — synthesize a worker REPORT.md from the worker's terminal message.

Why this exists:
  Specialist agents have their own write allow-lists that scope writes
  to their bounded artifact roots. When a worker session re-uses a
  specialist, the specialist's own contract refuses to write outside
  its sandbox — so it cannot write REPORT.md to
  ``.memex/.autopilot/runs/<runid>/<worker-id>/REPORT.md``.

  Rather than weaken every specialist's allow-list, the coordinator
  synthesizes REPORT.md from the worker's terminal message (which the
  Agent tool returns). The worker's only responsibility is to emit a
  final-line `STATUS: ok | failed | needs-input`.

Inputs (CLI):
  --run-id <run-id>           Coordinator run id.
  --worker-id <worker-id>     Worker id created during PLAN.
  --terminal-message <path>   Path to a file containing the worker's terminal message.
  --specialist-output-path <path>
                              Optional. Absolute path to the specialist's actual
                              report. Recorded in REPORT.md.
  --tokens <int>              Optional. Token usage reported by the Agent run.
  --tool-calls <int>          Optional. Tool-call count reported by the Agent run.
  --status-fallback           Optional flag. If the terminal message has no valid
                              trailing STATUS line, write `STATUS: needs-input`
                              instead of erroring.

Side effects:
  - Writes ``.memex/.autopilot/runs/<run-id>/<worker-id>/REPORT.md``.
  - Writes ``.memex/.autopilot/runs/<run-id>/<worker-id>/.done`` (empty marker).
  - Stdout: one line of the form ``SYNTH: <worker-id> STATUS: <status>``.

Stdlib only. Python 3.10+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_STATUSES = ("ok", "failed", "needs-input")

STATUS_LINE_RE = re.compile(r"^STATUS:\s*(ok|failed|needs-input)\s*$")


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_trailing_status(text: str) -> str | None:
    if not text:
        return None
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        match = STATUS_LINE_RE.match(stripped)
        if match:
            return match.group(1)
        return None
    return None


def strip_trailing_status_line(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and STATUS_LINE_RE.match(lines[-1].strip()):
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def render_report(
    run_id: str,
    worker_id: str,
    task: dict,
    body: str,
    status: str,
    specialist_output_path: str | None,
    tokens: int | None,
    tool_calls: int | None,
) -> str:
    kind = task.get("kind", "unknown")
    target = task.get("target", "")
    specialist = task.get("specialist", "")
    tokens_str = str(tokens) if tokens is not None else "n/a"
    tool_calls_str = str(tool_calls) if tool_calls is not None else "n/a"
    spec_path = specialist_output_path or "n/a (worker did not write a separate specialist artifact)"
    body_clean = strip_trailing_status_line(body or "").rstrip()
    return (
        f"# Worker report — {worker_id}\n\n"
        f"## Task\n"
        f"- kind: {kind}\n"
        f"- target: {target}\n"
        f"- runid: {run_id}\n\n"
        f"## Specialist invoked\n{specialist}\n\n"
        f"## Specialist output path\n{spec_path}\n\n"
        f"## Specialist terminal message\n{body_clean}\n\n"
        f"## Tokens used\n{tokens_str}\n\n"
        f"## Tool calls made\n{tool_calls_str}\n\n"
        f"## Notes\n"
        f"- REPORT.md synthesised by the coordinator (`coordinator_synth_report.py`) at {utcnow_iso()} "
        f"from the worker's terminal message.\n\n"
        f"STATUS: {status}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--terminal-message", required=True,
                        help="Path to file containing the worker's terminal message text")
    parser.add_argument("--specialist-output-path", default=None)
    parser.add_argument("--tokens", type=int, default=None)
    parser.add_argument("--tool-calls", type=int, default=None)
    parser.add_argument("--status-fallback", action="store_true",
                        help="If no trailing STATUS line found, fall back to needs-input")
    args = parser.parse_args()

    root = project_root()
    worker_dir = root / ".memex" / ".autopilot" / "runs" / args.run_id / args.worker_id
    worker_dir.mkdir(parents=True, exist_ok=True)

    task_path = worker_dir / "task.json"
    if task_path.is_file():
        try:
            task = json.loads(task_path.read_text(encoding="utf-8"))
        except Exception:
            task = {}
    else:
        task = {}

    msg_path = Path(args.terminal_message)
    if not msg_path.is_file():
        print(f"ERROR: terminal-message file not found: {msg_path}", file=sys.stderr)
        return 1
    body = msg_path.read_text(encoding="utf-8")

    status = parse_trailing_status(body)
    if status is None:
        if args.status_fallback:
            status = "needs-input"
        else:
            print(f"ERROR: no trailing STATUS: line in terminal message for {args.worker_id}; "
                  f"pass --status-fallback to default to needs-input", file=sys.stderr)
            return 2

    report_text = render_report(
        run_id=args.run_id,
        worker_id=args.worker_id,
        task=task,
        body=body,
        status=status,
        specialist_output_path=args.specialist_output_path,
        tokens=args.tokens,
        tool_calls=args.tool_calls,
    )
    (worker_dir / "REPORT.md").write_text(report_text, encoding="utf-8")
    (worker_dir / ".done").write_text("", encoding="utf-8")

    print(f"SYNTH: {args.worker_id} STATUS: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
