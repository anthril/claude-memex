#!/usr/bin/env python3
"""session-start-context.py — SessionStart hook

Emits the head of `index.md` and the last N entries of `log.md` as
`additionalContext` so Claude sees the wiki state at session boot.

N comes from `hookEvents.sessionStart.injectRecentLog` in the config,
default 5.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root


def read_lines(path: str, max_chars: int = 4000) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n... [truncated]"
    return content


def last_log_entries(log_path: str, n: int) -> str:
    try:
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""
    # Entries begin with `## [`; collect last N
    entries: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("## ["):
            if current:
                entries.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("".join(current))
    return "".join(entries[-n:]) if entries else ""


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

    opts = (cfg.get("hookEvents") or {}).get("sessionStart") or {}
    inject_index = opts.get("injectIndex", True)
    recent_n = int(opts.get("injectRecentLog", 5))

    ops_root = os.path.join(project_root, cfg["root"])
    index_path = os.path.join(ops_root, cfg.get("index", {}).get("path", "index.md"))
    log_path = os.path.join(ops_root, cfg.get("log", {}).get("path", "log.md"))

    parts = []
    if inject_index and os.path.isfile(index_path):
        parts.append("### Memex index (head)\n\n" + read_lines(index_path, 3000))
    if recent_n > 0 and os.path.isfile(log_path):
        recent = last_log_entries(log_path, recent_n)
        if recent:
            parts.append(f"### Memex log (last {recent_n} entries)\n\n{recent}")

    if not parts:
        sys.exit(0)

    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(parts)}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
