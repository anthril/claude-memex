"""Shared transcript-walking helpers for Stop / PreCompact hooks.

A Claude Code session transcript is a JSONL file: one JSON object per line,
each typically `{"message": {"content": [...]}}`. Tool-use blocks look like
`{"type": "tool_use", "name": "Write", "input": {"file_path": "..."}}`.

Multiple Stop hooks all needed to walk this file independently. This module
gives them one shared parse so the orchestrator can do it once.
"""
from __future__ import annotations

import json
import os


def collect_tool_writes(transcript_path: str) -> tuple[int, set[str]]:
    """Walk a transcript JSONL and return (write_count, touched_file_paths).

    `write_count` counts every Write or Edit tool_use block.
    `touched_file_paths` is the set of `file_path` inputs to those calls
    (raw — not normalised; callers normalise as needed).

    Returns `(0, set())` for missing / unreadable transcripts. Never raises.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return 0, set()
    writes = 0
    files: set[str] = set()
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
