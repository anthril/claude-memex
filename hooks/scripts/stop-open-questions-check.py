#!/usr/bin/env python3
"""stop-open-questions-check.py — Stop hook

Scans every markdown page under the ops root that was written/edited this
session for inline TODO/TBD/XXX/FIXME markers in prose. Emits a non-blocking
`additionalContext` message prompting Claude to promote them to
`.open-questions/` or a scoped `## Open questions` section.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root, normalise
from _lib.transcript import collect_tool_writes

MARKER_RE = re.compile(r"\b(TODO|TBD|XXX|FIXME)\b[:\s]")


def session_wiki_writes(transcript_path: str, ops_prefix: str) -> set[str]:
    """Backwards-compat wrapper: filter `collect_tool_writes` to wiki .md files."""
    _, raw = collect_tool_writes(transcript_path)
    return {
        fp for fp in raw
        if fp and ops_prefix in normalise(fp) and fp.endswith(".md")
    }


def filter_wiki_md_writes(files: set[str], ops_prefix: str) -> set[str]:
    """Pure helper used by run() — same shape as session_wiki_writes' output."""
    return {fp for fp in files if fp and ops_prefix in normalise(fp) and fp.endswith(".md")}


def scan_file(fp):
    hits = []
    try:
        with open(fp, encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if MARKER_RE.search(line):
                    # Skip lines that look like they're ALREADY in a `## Open questions` section —
                    # heuristic: the previous line heading contained "open questions"
                    hits.append((i, line.rstrip()))
    except Exception:
        pass
    return hits


def run(payload: dict, project_root: str, cfg: dict, writes: int, files: set[str]) -> str | None:
    """Scan touched wiki .md files for inline TODO/TBD/XXX/FIXME markers.

    Persists findings to `.memex/.state/inline-todos.json` for the docsite
    banner; returns additionalContext or None.
    """
    ops_prefix = "/" + cfg["root"].rstrip("/").split("/")[-1] + "/"
    written = filter_wiki_md_writes(files, ops_prefix)
    if not written:
        return None

    findings = []
    for fp in sorted(written):
        rel = os.path.relpath(fp, project_root).replace("\\", "/")
        hits = scan_file(fp)
        for lineno, text in hits:
            findings.append((rel, lineno, text.strip()[:160]))

    # Persist findings to `.memex/.state/inline-todos.json` so the docsite's
    # /open-questions page can surface them as an "Unpromoted TODOs" banner.
    # Best-effort — failure here doesn't change the existing additionalContext flow.
    if findings:
        try:
            state_dir = os.path.join(project_root, cfg["root"].rstrip("/"), ".state")
            os.makedirs(state_dir, exist_ok=True)
            state_path = os.path.join(state_dir, "inline-todos.json")
            payload_out = {
                "generated_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "findings": [
                    {"path": rel, "line": lineno, "text": text}
                    for rel, lineno, text in findings
                ],
            }
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(payload_out, fh, indent=2)
        except Exception:
            pass

    if not findings:
        return None

    lines = [
        "### Memex open-questions check",
        "",
        "Inline TODO/TBD/FIXME markers in wiki pages edited this session:",
        "",
    ]
    for rel, lineno, text in findings[:10]:
        lines.append(f"- `{rel}:{lineno}` — {text}")
    lines.append("")
    lines.append("Promote each to `.open-questions/<slug>.md` or to a scoped `## Open questions` section on the owning page. Do NOT leave them inline.")
    return "\n".join(lines)


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
    ctx = run(payload, project_root, cfg, writes, files)
    if ctx:
        out = {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": ctx}}
        sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
