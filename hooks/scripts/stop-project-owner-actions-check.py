#!/usr/bin/env python3
"""stop-project-owner-actions-check.py — Stop hook

Scans markdown pages and (when present) plan files written/edited this session
for phrases indicating that a step requires action by a real human owner — not
something an agent can do. Suggests promoting them to
`.memex/.project-owner-actions/<slug>.md` via `/memex:owner-action`.

Detection is heuristic. False positives are intentional — the hook nudges, it
doesn't block. The Claude session can ignore the suggestion if the phrase is
descriptive (e.g. quoting a past resolution) rather than prescriptive.

Also surfaces a count of pending project-owner actions whose `target_close_date`
is in the past (overdue). Both signals appear in the same `additionalContext`
block so the user / next session sees the full picture.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root, normalise

# Phrases that strongly suggest an action the project owner must take.
# Word-boundary anchored to avoid matching mid-word noise.
OWNER_PHRASES = [
    r"project[- ]owner action(?:s)? only",
    r"project[- ]owner action(?:s)? required",
    r"requires? project[- ]owner",
    r"only the project[- ]owner can",
    r"cannot be done by (?:claude|an agent|the agent)",
    r"external action only",
    r"external coordination required",
    r"needs? a real human",
    r"requires? a real signature",
    r"requires? human approval",
    r"out[- ]of[- ]band(?:,|\.)? (?:project[- ]owner|external|human)",
    r"pending external action",
    r"awaiting (?:legal|ethics|payment|osf|irb|mou) (?:sign[- ]?off|approval|filing)",
    r"blocked on (?:project[- ]owner|external|human|legal|ethics|osf|irb)",
]

OWNER_RE = re.compile("|".join(OWNER_PHRASES), re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"^---\s*$", re.MULTILINE)
TARGET_CLOSE_RE = re.compile(r"^target_close_date:\s*([^\s]+)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^status:\s*([^\s]+)\s*$", re.MULTILINE)


def session_writes(transcript_path: str) -> set[str]:
    """All Write/Edit file paths the agent touched this session."""
    files: set[str] = set()
    if not transcript_path or not os.path.isfile(transcript_path):
        return files
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                blocks = (msg.get("message") or {}).get("content") or []
                if not isinstance(blocks, list):
                    continue
                for b in blocks:
                    if (
                        isinstance(b, dict)
                        and b.get("type") == "tool_use"
                        and b.get("name") in ("Write", "Edit")
                    ):
                        fp = (b.get("input") or {}).get("file_path")
                        if fp:
                            files.add(fp)
    except Exception:
        pass
    return files


def scan_file_for_owner_phrases(fp: str) -> list[tuple[int, str]]:
    """Return (line_no, line_text) for every line containing an owner phrase."""
    if not os.path.isfile(fp):
        return []
    hits: list[tuple[int, str]] = []
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, start=1):
                if OWNER_RE.search(line):
                    hits.append((i, line.rstrip()))
    except Exception:
        pass
    return hits


def list_pending_owner_actions(project_root: str, root: str) -> list[dict]:
    """Walk `.project-owner-actions/` and return pending entries with target dates."""
    actions_dir = os.path.join(project_root, root.rstrip("/"), ".project-owner-actions")
    if not os.path.isdir(actions_dir):
        return []
    entries: list[dict] = []
    for name in os.listdir(actions_dir):
        if name.startswith(".") or not name.endswith(".md") or name == "README.md":
            continue
        fp = os.path.join(actions_dir, name)
        try:
            with open(fp, encoding="utf-8") as f:
                head = f.read(2048)
        except Exception:
            continue
        status_m = STATUS_RE.search(head)
        target_m = TARGET_CLOSE_RE.search(head)
        status = status_m.group(1) if status_m else "unknown"
        target = target_m.group(1) if target_m else "<unscheduled>"
        if status not in ("completed", "cancelled"):
            entries.append({"path": fp, "name": name, "status": status, "target": target})
    return entries


def overdue(entries: list[dict]) -> list[dict]:
    today = date.today()
    out = []
    for e in entries:
        t = e["target"].strip("<>")
        if t in ("unscheduled", ""):
            continue
        try:
            d = datetime.strptime(t, "%Y-%m-%d").date()
            if d < today:
                out.append(e)
        except Exception:
            continue
    return out


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project_root = find_project_root(cwd)
    if not project_root:
        sys.exit(0)
    cfg = load_config_from(project_root)
    if not cfg:
        sys.exit(0)

    root = cfg["root"]
    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or ""

    # Findings part 1: owner-phrase hits in session writes that aren't already in
    # `.project-owner-actions/` (no point flagging files in that folder — they're
    # the right place by definition).
    written = session_writes(transcript_path)
    actions_prefix = normalise(
        os.path.join(project_root, root.rstrip("/"), ".project-owner-actions")
    )
    phrase_findings: list[tuple[str, int, str]] = []
    for fp in sorted(written):
        if normalise(fp).startswith(actions_prefix):
            continue
        if not fp.endswith((".md", ".mdx", ".rst", ".txt")):
            continue
        for lineno, text in scan_file_for_owner_phrases(fp):
            try:
                rel = os.path.relpath(fp, project_root).replace("\\", "/")
            except Exception:
                rel = fp
            phrase_findings.append((rel, lineno, text.strip()[:160]))

    # Findings part 2: pending project-owner actions with overdue close dates.
    pending = list_pending_owner_actions(project_root, root)
    overdue_entries = overdue(pending)

    # Persist a state snapshot so the docsite can surface a banner.
    if pending or phrase_findings:
        try:
            state_dir = os.path.join(project_root, root.rstrip("/"), ".state")
            os.makedirs(state_dir, exist_ok=True)
            state_path = os.path.join(state_dir, "project-owner-actions.json")
            payload_out = {
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pending_count": len(pending),
                "overdue_count": len(overdue_entries),
                "pending": [
                    {"name": e["name"], "status": e["status"], "target_close_date": e["target"]}
                    for e in pending
                ],
                "phrase_findings": [
                    {"path": rel, "line": lineno, "text": text}
                    for rel, lineno, text in phrase_findings
                ],
            }
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(payload_out, fh, indent=2)
        except Exception:
            pass

    if not phrase_findings and not overdue_entries:
        sys.exit(0)

    lines = ["### Memex project-owner-actions check", ""]

    if phrase_findings:
        lines.append("Possible unfiled project-owner actions in pages edited this session:")
        lines.append("")
        for rel, lineno, text in phrase_findings[:10]:
            lines.append(f"- `{rel}:{lineno}` — {text}")
        if len(phrase_findings) > 10:
            lines.append(f"- … and {len(phrase_findings) - 10} more")
        lines.append("")
        lines.append(
            "If any of these describe a thing only the project owner can do "
            "(signatures, accounts, MOUs, money, naming a real human), file it "
            "with `/memex:owner-action <title>` so the dependency is tracked "
            "and surfaced to the next session."
        )
        lines.append("")

    if overdue_entries:
        lines.append(
            f"Overdue project-owner actions ({len(overdue_entries)} of {len(pending)} pending):"
        )
        lines.append("")
        for e in overdue_entries[:10]:
            lines.append(
                f"- `.project-owner-actions/{e['name']}` "
                f"— status `{e['status']}`, target_close_date `{e['target']}`"
            )
        if len(overdue_entries) > 10:
            lines.append(f"- … and {len(overdue_entries) - 10} more overdue")
        lines.append("")
        lines.append(
            "Consider: ping the project owner, push the target date, or "
            "downgrade severity if the blocker is no longer load-bearing."
        )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
