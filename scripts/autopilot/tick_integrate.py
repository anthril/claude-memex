"""INTEGRATE phase — validate worker REPORT.md files and route artifacts.

Reads:
  * runs/<run-id>/<worker-id>/REPORT.md (one per worker)
  * runs/<run-id>/<worker-id>/.done (presence; written by SubagentStop hook)

Writes:
  * .memex/.inbox/<run-id>/<artifact>.md (per worker, routed by task.kind + STATUS)
  * .memex/.inbox/INBOX.md (one-line index per artifact added)
  * .memex/.inbox/quarantine/<worker-id>/REPORT.md (if STATUS: failed)
  * runs/<run-id>/SUMMARY.md (human-readable tick summary)

Nothing is auto-committed. All worker outputs land in `.memex/.inbox/`
for human review.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_STATUSES = {"STATUS: ok", "STATUS: failed", "STATUS: needs-input"}


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_status(report_text: str) -> str | None:
    if not report_text:
        return None
    for line in reversed(report_text.splitlines()):
        s = line.strip()
        if not s:
            continue
        if s in VALID_STATUSES:
            return s.split(": ", 1)[1]
        return None
    return None


def append_inbox_index(inbox_dir: Path, run_id: str, artifact_rel: str, summary: str) -> None:
    index = inbox_dir / "INBOX.md"
    line = f"- [{run_id}/{artifact_rel}](./{run_id}/{artifact_rel}) — {summary}"
    if not index.is_file():
        index.write_text(
            "# Memex Autopilot — Inbox index\n\nOne line per inbox item, oldest first.\n\n",
            encoding="utf-8",
        )
    text = index.read_text(encoding="utf-8")
    if line in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    text += line + "\n"
    index.write_text(text, encoding="utf-8")


def route_oq_investigation(run_id: str, worker_id: str, target: str, report_text: str, root: Path) -> Path:
    inbox = root / ".memex" / ".inbox" / run_id
    inbox.mkdir(parents=True, exist_ok=True)
    out = inbox / f"oq-resolution-{target}.md"
    body = (
        f"# Inbox: OQ resolution sketch — {target}\n\n"
        f"- run_id: {run_id}\n"
        f"- worker_id: {worker_id}\n"
        f"- target: {target}\n"
        f"- ts: {utcnow_iso()}\n\n"
        "## Worker report\n\n" + report_text + "\n\n"
        "## Suggested next step (human action)\n\n"
        "Review the recommended resolution path. If you accept it, append a `## Resolution` "
        f"section to `.memex/.open-questions/{target}.md` and move the file to "
        "`.memex/.open-questions/.resolved/`.\n"
    )
    out.write_text(body, encoding="utf-8")
    return out


def route_owner_action(run_id: str, worker_id: str, target: str, report_text: str, root: Path) -> Path:
    inbox = root / ".memex" / ".inbox" / run_id
    inbox.mkdir(parents=True, exist_ok=True)
    out = inbox / f"owner-action-triage-{target}.md"
    body = (
        f"# Inbox: project-owner action triage — {target}\n\n"
        f"- run_id: {run_id}\n"
        f"- worker_id: {worker_id}\n"
        f"- target: {target}\n"
        f"- ts: {utcnow_iso()}\n\n"
        "## Worker report\n\n" + report_text + "\n\n"
        "## Suggested next step (human action)\n\n"
        f"Review the suggested next step on `.memex/.project-owner-actions/{target}.md`. "
        "Update the action's status field and (if the next step is now blocked on someone "
        "external) add a note to the action's body.\n"
    )
    out.write_text(body, encoding="utf-8")
    return out


def quarantine_failed(run_id: str, worker_id: str, kind: str, target: str, report_text: str, root: Path) -> Path:
    qdir = root / ".memex" / ".inbox" / "quarantine" / run_id
    qdir.mkdir(parents=True, exist_ok=True)
    out = qdir / f"{worker_id}.md"
    body = (
        f"# Quarantined worker — {worker_id}\n\n"
        f"- kind: {kind}\n"
        f"- target: {target}\n"
        f"- run_id: {run_id}\n"
        f"- ts: {utcnow_iso()}\n\n"
        "## Worker report\n\n" + report_text + "\n"
    )
    out.write_text(body, encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = project_root()
    run_dir = root / ".memex" / ".autopilot" / "runs" / args.run_id
    inbox_root = root / ".memex" / ".inbox"

    summary_lines = [
        f"# Tick summary — {args.run_id}",
        "",
        f"- ts: {utcnow_iso()}",
        "",
        "## Workers",
        "",
    ]
    counts = {"ok": 0, "failed": 0, "needs-input": 0, "missing": 0}
    inbox_added = 0

    for worker_dir in sorted(run_dir.glob("*/")):
        if not worker_dir.is_dir():
            continue
        worker_id = worker_dir.name
        if worker_id in {"perceive.json", "plan.json", "SUMMARY.md", "tick.log"}:
            continue
        task_path = worker_dir / "task.json"
        if not task_path.is_file():
            continue
        try:
            task = json.loads(task_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        kind = task.get("kind", "unknown")
        target = task.get("target", "")

        report_path = worker_dir / "REPORT.md"
        if not report_path.is_file():
            counts["missing"] += 1
            summary_lines.append(f"- {worker_id} ({kind}: {target}) — no REPORT.md (worker died)")
            quarantine_failed(args.run_id, worker_id, kind, target,
                              "REPORT.md missing entirely. Worker likely died before write_report().", root)
            continue

        report_text = report_path.read_text(encoding="utf-8")
        status = parse_status(report_text)
        if status is None:
            counts["failed"] += 1
            summary_lines.append(f"- {worker_id} ({kind}: {target}) — invalid STATUS line")
            quarantine_failed(args.run_id, worker_id, kind, target, report_text, root)
            continue
        counts[status] += 1
        summary_lines.append(f"- {worker_id} ({kind}: {target}) — STATUS: {status}")

        if status == "failed":
            quarantine_failed(args.run_id, worker_id, kind, target, report_text, root)
            continue

        routed: Path | None = None
        if kind == "oq-investigate":
            routed = route_oq_investigation(args.run_id, worker_id, target, report_text, root)
        elif kind == "owner-action-triage":
            routed = route_owner_action(args.run_id, worker_id, target, report_text, root)

        if routed is not None:
            inbox_added += 1
            artifact_rel = routed.relative_to(inbox_root / args.run_id).as_posix()
            append_inbox_index(inbox_root, args.run_id, artifact_rel,
                               f"{kind} {target} — STATUS: {status}")

    summary_lines.append("")
    summary_lines.append(
        f"## Totals\n\n- ok: {counts['ok']}\n- failed: {counts['failed']}\n"
        f"- needs-input: {counts['needs-input']}\n- missing: {counts['missing']}\n"
        f"- inbox items added: {inbox_added}\n- auto-committed: 0 (all artifacts route to .memex/.inbox/)\n"
    )
    (run_dir / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(
        f"INTEGRATE: {counts['ok']} ok, {counts['failed']} failed, "
        f"{counts['needs-input']} needs-input, {counts['missing']} missing; "
        f"{inbox_added} inbox items added"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
