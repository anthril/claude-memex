#!/usr/bin/env python3
"""session-end-log.py — SessionEnd hook

Final log entry on session end. Mirrors `stop-log-append` but fires only
once, at actual session termination. Useful for the "Agents Behaving Badly"
research angle — gives a clean delimiter between sessions in `log.md`.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root


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

    log_rel = cfg.get("log", {}).get("path", "log.md")
    log_path = os.path.join(project_root, cfg["root"], log_rel)
    if not os.path.isfile(log_path):
        sys.exit(0)

    reason = payload.get("reason") or payload.get("endReason") or "closed"
    template = cfg.get("log", {}).get("entryPrefix", "## [{date}] {event} | {subject}")
    date = datetime.date.today().isoformat()
    header = template.format(date=date, event="session-end", subject=f"reason: {reason}")

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + header + "\n")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
