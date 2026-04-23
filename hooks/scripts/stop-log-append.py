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


def count_tool_calls(transcript_path: str):
    if not transcript_path or not os.path.isfile(transcript_path):
        return 0, set()
    writes = 0
    files = set()
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
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit"):
                        writes += 1
                        fp = (b.get("input") or {}).get("file_path")
                        if fp:
                            files.add(fp)
    except Exception:
        pass
    return writes, files


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

    opts = (cfg.get("hookEvents") or {}).get("stop") or {}
    if opts.get("appendLog", True) is False:
        sys.exit(0)

    log_rel = cfg.get("log", {}).get("path", "log.md")
    log_path = os.path.join(project_root, cfg["root"], log_rel)
    if not os.path.isfile(log_path):
        sys.exit(0)

    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    writes, files = count_tool_calls(transcript_path)

    if writes == 0:
        # Nothing to log
        sys.exit(0)

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

    sys.exit(0)


if __name__ == "__main__":
    main()
