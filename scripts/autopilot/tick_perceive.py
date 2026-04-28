"""PERCEIVE phase — snapshot the Memex backlog and write perceive.json.

Reads (read-only):
  * .memex/.open-questions/*.md         (active OQs)
  * .memex/.project-owner-actions/*.md  (active owner actions)
  * git log since state.json:last_tick_at
  * .memex/.inbox/                      (count of awaiting items)
  * .memex/.open-questions/.resolved/   (resolved count)

Writes:
  * .memex/.autopilot/runs/<run-id>/perceive.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: dict[str, str] = {}
    for line in parts[1].splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip().strip('"').strip("'")
    return out


def _scan_md_dir(
    dir_path: Path,
    project_root_path: Path,
) -> list[dict]:
    if not dir_path.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(dir_path.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        slug = path.stem
        fm = parse_frontmatter(text)

        sev = fm.get("severity") or fm.get("Severity") or "MEDIUM"
        m = re.search(r"(?i)\bseverity\b\s*[:|]\s*(HIGH|MEDIUM|LOW|CRITICAL)\b", text)
        if m:
            sev = m.group(1).upper()
        sev = (sev or "MEDIUM").upper()

        deadline = fm.get("target_close_date") or fm.get("target-close-date") or ""
        if not deadline:
            m = re.search(r"(?i)target\s*close\s*date\s*[:|]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
            if m:
                deadline = m.group(1)

        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0

        out.append({
            "slug": slug,
            "severity": sev,
            "target_close_date": deadline,
            "status": (fm.get("status") or "").lower(),
            "owner": fm.get("owner") or "",
            "mtime": mtime,
            "path": str(path.relative_to(project_root_path).as_posix()),
        })
    return out


def scan_open_questions(root: Path) -> list[dict]:
    items = _scan_md_dir(root / ".memex" / ".open-questions", root)
    return [it for it in items if it.get("status", "") not in ("resolved", "archived")]


def scan_owner_actions(root: Path) -> list[dict]:
    items = _scan_md_dir(root / ".memex" / ".project-owner-actions", root)
    return [it for it in items if it.get("status", "") not in ("done", "completed", "archived")]


def commits_since(root: Path, since: str | None) -> list[str]:
    args = ["git", "log", "--oneline", "-50"]
    if since:
        args = ["git", "log", "--oneline", f"--since={since}"]
    try:
        out = subprocess.run(args, cwd=str(root), capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            return []
        return out.stdout.strip().splitlines()
    except Exception:
        return []


def count_inbox(root: Path) -> int:
    inbox = root / ".memex" / ".inbox"
    if not inbox.is_dir():
        return 0
    n = 0
    for p in inbox.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(inbox).as_posix()
        except ValueError:
            continue
        if rel.startswith("quarantine/"):
            continue
        if p.name == ".gitkeep" or rel == "INBOX.md":
            continue
        n += 1
    return n


def count_resolved_oqs(root: Path) -> int:
    rdir = root / ".memex" / ".open-questions" / ".resolved"
    if not rdir.is_dir():
        return 0
    return sum(1 for p in rdir.glob("*.md") if p.name != "README.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--maintenance", default="false")
    args = parser.parse_args()

    root = project_root()
    run_dir = root / ".memex" / ".autopilot" / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    state_path = root / ".memex" / ".autopilot" / "state.json"
    state = {}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    last_tick = state.get("last_tick_at")

    snapshot = {
        "ts": utcnow_iso(),
        "run_id": args.run_id,
        "maintenance": args.maintenance.lower() == "true",
        "oqs": scan_open_questions(root),
        "owner_actions": scan_owner_actions(root),
        "commits_since_last_tick": commits_since(root, last_tick),
        "inbox_count": count_inbox(root),
        "resolved_oq_count": count_resolved_oqs(root),
    }

    out_path = run_dir / "perceive.json"
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"PERCEIVE: {len(snapshot['oqs'])} OQs, "
        f"{len(snapshot['owner_actions'])} owner-actions, "
        f"{len(snapshot['commits_since_last_tick'])} commits, "
        f"{snapshot['inbox_count']} inbox"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
