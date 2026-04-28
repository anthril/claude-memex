"""LEARN phase — update heuristics + checkpoint state.json.

Reads:
  * runs/<run-id>/SUMMARY.md (counts of ok/failed/needs-input/missing)
  * runs/<run-id>/<worker-id>/task.json (kind, target, attempts)

Writes:
  * state.json (incremented tick_count, updated heuristics, exponential_backoff)
  * history.jsonl (tick_complete entry)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_summary(text: str) -> dict[str, int]:
    out = {"ok": 0, "failed": 0, "needs-input": 0, "missing": 0}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*(ok|failed|needs-input|missing)\s*:\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--next-eta-min", type=int, default=90)
    args = parser.parse_args()

    root = project_root()
    run_dir = root / ".memex" / ".autopilot" / "runs" / args.run_id
    state_path = root / ".memex" / ".autopilot" / "state.json"
    history_path = root / ".memex" / ".autopilot" / "history.jsonl"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    summary_path = run_dir / "SUMMARY.md"
    counts = {"ok": 0, "failed": 0, "needs-input": 0, "missing": 0}
    if summary_path.is_file():
        counts = parse_summary(summary_path.read_text(encoding="utf-8"))

    heuristics = state.setdefault("heuristics", {})
    success = heuristics.setdefault("task_kind_success_rate", {})
    backoff = heuristics.setdefault("exponential_backoff", {})

    BACKOFF_DELTAS = {1: 60, 2: 360, 3: 1440}

    for worker_dir in sorted(run_dir.glob("*/")):
        if not worker_dir.is_dir():
            continue
        task_path = worker_dir / "task.json"
        report_path = worker_dir / "REPORT.md"
        if not task_path.is_file():
            continue
        try:
            task = json.loads(task_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        kind = task.get("kind", "unknown")
        target = task.get("target", "")
        status = "missing"
        if report_path.is_file():
            text = report_path.read_text(encoding="utf-8")
            for line in reversed(text.splitlines()):
                s = line.strip()
                if not s:
                    continue
                if s.startswith("STATUS: "):
                    status = s.split(": ", 1)[1]
                break

        prev = success.get(kind, 0.5)
        observed = 1.0 if status == "ok" else 0.0
        success[kind] = round(0.8 * prev + 0.2 * observed, 4)

        bkey = f"{kind}:{target}"
        if status in {"failed", "missing"}:
            entry = backoff.get(bkey, {"failures": 0})
            entry["failures"] = int(entry.get("failures", 0)) + 1
            delta = BACKOFF_DELTAS.get(min(entry["failures"], 3), 1440)
            entry["next_eligible_at"] = (datetime.now(timezone.utc) + timedelta(minutes=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")
            backoff[bkey] = entry
        else:
            backoff.pop(bkey, None)

    state["tick_count"] = int(state.get("tick_count", 0)) + 1
    state["last_tick_at"] = utcnow_iso()
    state["next_tick_eta"] = (datetime.now(timezone.utc) + timedelta(minutes=args.next_eta_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_modified_at"] = utcnow_iso()

    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    history_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": utcnow_iso(),
        "phase": "tick_complete",
        "run_id": args.run_id,
        "tick_count": state["tick_count"],
        "counts": counts,
    }
    with open(history_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    print(f"LEARN: tick_count={state['tick_count']}, next_tick_eta={state['next_tick_eta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
