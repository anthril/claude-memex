#!/usr/bin/env python3
"""stop-log-append.py — Stop hook

Appends a chronological entry to `log.md` summarising the session. Uses the
prefix template from `log.entryPrefix`.

This hook does minimal work — it doesn't try to synthesise the session
narrative itself (the `scribe-ingestor`/`memex-ingestor` skills do that when
invoked). It just stamps the log so the session is visible in the history.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root
from _lib.transcript import collect_tool_writes


def count_tool_calls(transcript_path: str):
    """Backwards-compatible wrapper around `_lib.transcript.collect_tool_writes`."""
    return collect_tool_writes(transcript_path)


def run(payload: dict, project_root: str, cfg: dict, writes: int, files: set[str]) -> str | None:
    """Append a session entry to log.md. Returns no additionalContext (always None).

    Idempotent shape: takes pre-parsed transcript inputs so the orchestrator
    can avoid re-walking the JSONL. Side-effect only — writes one line to log.md.
    """
    opts = (cfg.get("hookEvents") or {}).get("stop") or {}
    if opts.get("appendLog", True) is False:
        return None

    log_rel = cfg.get("log", {}).get("path", "log.md")
    log_path = os.path.join(project_root, cfg["root"], log_rel)
    if not os.path.isfile(log_path):
        return None

    if writes == 0:
        return None

    ops_prefix = (cfg["root"].rstrip("/").split("/")[-1]) + "/"
    ops_touched = sorted({
        os.path.relpath(fp, project_root).replace("\\", "/")
        for fp in files
        if ops_prefix in fp.replace("\\", "/")
    })
    subject = f"{writes} write(s)" + (f"; touched: {', '.join(ops_touched[:3])}" + ("..." if len(ops_touched) > 3 else "") if ops_touched else "")

    template = cfg.get("log", {}).get("entryPrefix", "## [{date}] {event} | {subject}")
    date = datetime.date.today().isoformat()
    header = template.format(date=date, event="session", subject=subject)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + header + "\n")
    except Exception:
        pass

    return None


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

    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    writes, files = collect_tool_writes(transcript_path)
    run(payload, project_root, cfg, writes, files)
    sys.exit(0)


if __name__ == "__main__":
    main()
