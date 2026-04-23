#!/usr/bin/env python3
"""precompact-snapshot.py — PreCompact hook

Writes a lightweight session snapshot to `.memex/.state/sessions/<id>.md`
before the conversation compacts. This preserves the synthesis that would
otherwise be lost at the compaction boundary.

The snapshot is deliberately small: session id, date, a summary of tool
calls, and pointers to touched pages. Full session summarisation is the job
of the `ingest-source` / `memex-planner` skills — not of a silent hook.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root, normalise


def count_events(transcript_path: str) -> tuple[dict[str, int], set[str]]:
    tools: dict[str, int] = {}
    files: set[str] = set()
    if not transcript_path or not os.path.isfile(transcript_path):
        return tools, files
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
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        name = b.get("name") or "?"
                        tools[name] = tools.get(name, 0) + 1
                        fp = (b.get("input") or {}).get("file_path")
                        if fp:
                            files.add(normalise(fp))
    except Exception:
        pass
    return tools, files


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

    opts = (cfg.get("hookEvents") or {}).get("preCompact") or {}
    if opts.get("snapshot", True) is False:
        sys.exit(0)

    session_id = payload.get("session_id") or payload.get("sessionId") or "unknown"
    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    tools, files = count_events(transcript_path)

    snapshot_dir = os.path.join(project_root, cfg["root"], ".state", "sessions")
    try:
        os.makedirs(snapshot_dir, exist_ok=True)
    except Exception:
        sys.exit(0)

    date = datetime.datetime.now().isoformat(timespec="seconds")
    lines = [
        f"# Session snapshot — {session_id}",
        "",
        f"- Captured: {date} (PreCompact)",
        f"- Project root: `{project_root}`",
        "",
        "## Tool usage",
        "",
    ]
    if tools:
        for name, count in sorted(tools.items(), key=lambda x: -x[1]):
            lines.append(f"- {name}: {count}")
    else:
        lines.append("- (none recorded)")

    if files:
        lines.append("")
        lines.append("## Files touched")
        lines.append("")
        for fp in sorted(files)[:50]:
            lines.append(f"- `{fp}`")

    try:
        with open(os.path.join(snapshot_dir, f"{session_id}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
