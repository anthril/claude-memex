"""Lifecycle helper for Memex Autopilot — pause / resume / status / uninstall.

Stdlib only. Python 3.10+. Designed to be invoked by the four
`/memex:autopilot-pause|resume|status|uninstall` slash commands.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LOOP_DIR = ".memex/.autopilot"
INBOX_DIR = ".memex/.inbox"


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def relative_time(when_iso: str | None) -> str:
    if not when_iso:
        return ""
    try:
        when = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        secs = int((now - when).total_seconds())
        future = secs < 0
        secs = abs(secs)
        if secs < 60:
            label = f"{secs}s"
        elif secs < 3600:
            label = f"{secs // 60}m"
        elif secs < 86400:
            label = f"{secs // 3600}h"
        else:
            label = f"{secs // 86400}d"
        return f"in {label}" if future else f"{label} ago"
    except Exception:
        return ""


def append_history(root: Path, record: dict) -> None:
    history = root / LOOP_DIR / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    record = dict(record)
    record.setdefault("ts", utcnow_iso())
    with open(history, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def assert_installed(root: Path) -> bool:
    state = root / LOOP_DIR / "state.json"
    if not state.is_file():
        print("Autopilot not installed. Run /memex:autopilot-install.")
        return False
    return True


def cmd_pause(args, root: Path) -> int:
    if not assert_installed(root):
        return 0
    paused = root / LOOP_DIR / "PAUSED"
    reason = (args.reason or "manual").strip() or "manual"
    if paused.exists():
        first = (paused.read_text(encoding="utf-8").splitlines() or ["<no content>"])[0]
        print(f"Already paused. {first}")
        return 0
    paused.parent.mkdir(parents=True, exist_ok=True)
    line = f"{utcnow_iso()} | reason: {reason}"
    paused.write_text(line + "\n", encoding="utf-8")
    append_history(root, {"phase": "paused", "reason": reason})
    print(
        f"Memex Autopilot PAUSED at {utcnow_iso()}.\n"
        f"Reason: {reason}\n"
        "The next tick (cron heartbeat) will see this file and exit cleanly.\n"
        "To resume: /memex:autopilot-resume"
    )
    return 0


def cmd_resume(args, root: Path) -> int:
    if not assert_installed(root):
        return 0
    paused = root / LOOP_DIR / "PAUSED"
    if not paused.exists():
        print("Already running (no PAUSED file).")
        return 0
    first = (paused.read_text(encoding="utf-8").splitlines() or ["<no content>"])[0]
    paused.unlink()
    append_history(root, {"phase": "resumed", "previous_pause": first})
    print(
        "Memex Autopilot RESUMED.\n"
        f"Was paused: {first}\n"
        "Next tick will proceed (next cron heartbeat)."
    )
    return 0


def _scan_inbox(inbox_root: Path) -> tuple[int, list[tuple[Path, float]]]:
    if not inbox_root.is_dir():
        return 0, []
    items: list[tuple[Path, float]] = []
    for p in inbox_root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(inbox_root).as_posix()
        except ValueError:
            continue
        if rel.startswith("quarantine/"):
            continue
        if p.name == ".gitkeep" or rel == "INBOX.md":
            continue
        try:
            items.append((p, p.stat().st_mtime))
        except Exception:
            pass
    items.sort(key=lambda t: t[1])
    return len(items), items[:3]


def _count_quarantine(inbox_root: Path) -> int:
    q = inbox_root / "quarantine"
    if not q.is_dir():
        return 0
    return sum(1 for p in q.rglob("*") if p.is_file() and p.name != ".gitkeep")


def cmd_status(args, root: Path) -> int:
    if not assert_installed(root):
        return 0
    loop_dir = root / LOOP_DIR
    inbox_root = root / INBOX_DIR
    state = json.loads((loop_dir / "state.json").read_text(encoding="utf-8"))

    paused = loop_dir / "PAUSED"
    paused_line = "no"
    if paused.exists():
        first = (paused.read_text(encoding="utf-8").splitlines() or ["<unknown>"])[0]
        paused_line = f"YES — {first}"

    rl = loop_dir / "RATE-LIMITED"
    rl_line = "yes" if rl.exists() else "no"

    budget = "?"
    try:
        budget = int((loop_dir / "BUDGET").read_text(encoding="utf-8").strip().splitlines()[0])
    except Exception:
        pass

    in_flight = state.get("in_flight") or []
    inbox_count, inbox_top = _scan_inbox(inbox_root)
    qcount = _count_quarantine(inbox_root)
    heuristics = state.get("heuristics") or {}

    last_tick = state.get("last_tick_at")
    next_eta = state.get("next_tick_eta")

    lines = [
        "## Memex Autopilot status",
        f"- schema_version: {state.get('schema_version')}",
        f"- tick_count: {int(state.get('tick_count') or 0)}",
        f"- last_tick_at: {last_tick or 'never'} ({relative_time(last_tick) if last_tick else 'n/a'})",
        f"- next_tick_eta: {next_eta or 'n/a'} ({relative_time(next_eta) if next_eta else 'n/a'})",
        f"- in_flight workers: {len(in_flight)}",
    ]
    for w in in_flight[:3]:
        if isinstance(w, dict):
            lines.append(
                f"    - {w.get('worker_id', '?')}: {w.get('task_kind', '?')} "
                f"{w.get('target', '')} (started {relative_time(w.get('started_at'))})"
            )
    lines.append(f"- inbox awaiting review: {inbox_count}")
    for path, ts in inbox_top:
        try:
            rel = path.relative_to(inbox_root).as_posix()
        except ValueError:
            rel = str(path)
        when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"    - {rel} ({relative_time(when)})")
    lines.append(f"- quarantined tasks: {qcount}")
    lines.append(f"- PAUSED: {paused_line}")
    lines.append(f"- RATE-LIMITED: {rl_line}")
    lines.append(f"- budget remaining today: {budget} sessions")
    success_rates = heuristics.get("task_kind_success_rate") or {}
    if success_rates:
        sr = ", ".join(f"{k}={v}" for k, v in sorted(success_rates.items()))
        lines.append(f"- heuristics.success_rate: {sr}")

    print("\n".join(lines))

    if args.verbose:
        print("\n## state.json")
        print(json.dumps(state, indent=2, sort_keys=True))
        history_path = loop_dir / "history.jsonl"
        if history_path.is_file():
            print("\n## last 5 history entries")
            history_lines = history_path.read_text(encoding="utf-8").splitlines()
            for line in history_lines[-5:]:
                print(line)
    return 0


def cmd_uninstall(args, root: Path) -> int:
    loop_dir = root / LOOP_DIR
    if not loop_dir.is_dir():
        print("Autopilot not installed (or already uninstalled).")
        return 0

    paused = loop_dir / "PAUSED"
    if not paused.exists():
        paused.write_text(f"{utcnow_iso()} | reason: uninstall in progress\n", encoding="utf-8")

    ids_path = loop_dir / "scheduled-task-ids.json"
    cron_ids = []
    if ids_path.is_file():
        try:
            cron_ids = json.loads(ids_path.read_text(encoding="utf-8"))
        except Exception:
            cron_ids = []

    archive_target = ""
    if not args.keep_state:
        ts = utcnow_iso().replace(":", "-")
        archive_path = loop_dir.parent / f".autopilot.archived-{ts}"
        shutil.move(str(loop_dir), str(archive_path))
        archive_target = str(archive_path)

    print(
        "Memex Autopilot uninstalled.\n"
        f"- Cron task IDs to deregister: {cron_ids if cron_ids else 'none recorded'}\n"
        f"- State: {('archived at ' + archive_target) if archive_target else 'kept (--keep-state)'}\n"
        "- Hooks: still loaded by the memex plugin (no-op without state); "
        "they short-circuit when .memex/.autopilot/ is absent.\n\n"
        "To reinstall: /memex:autopilot-install"
    )
    if cron_ids:
        print(
            "\nNote: cron deregistration requires a scheduled-tasks tool. "
            "Run: for each id, mcp__scheduled-tasks__update_scheduled_task(taskId=<id>, enabled=False)."
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_pause = sub.add_parser("pause")
    p_pause.add_argument("--reason", default="")
    sub.add_parser("resume")
    p_status = sub.add_parser("status")
    p_status.add_argument("--verbose", action="store_true")
    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("--keep-state", action="store_true")
    args = parser.parse_args()
    root = project_root()
    if args.cmd == "pause":
        return cmd_pause(args, root)
    if args.cmd == "resume":
        return cmd_resume(args, root)
    if args.cmd == "status":
        return cmd_status(args, root)
    if args.cmd == "uninstall":
        return cmd_uninstall(args, root)
    return 2


if __name__ == "__main__":
    sys.exit(main())
