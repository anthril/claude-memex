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

MARKER_RE = re.compile(r"\b(TODO|TBD|XXX|FIXME)\b[:\s]")


def session_wiki_writes(transcript_path: str, ops_prefix: str) -> set[str]:
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
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit"):
                        fp = (b.get("input") or {}).get("file_path")
                        if fp and ops_prefix in normalise(fp) and fp.endswith(".md"):
                            files.add(fp)
    except Exception:
        pass
    return files


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

    ops_prefix = "/" + cfg["root"].rstrip("/").split("/")[-1] + "/"
    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    written = session_wiki_writes(transcript_path, ops_prefix)
    if not written:
        sys.exit(0)

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
        sys.exit(0)

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

    out = {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "\n".join(lines)}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
