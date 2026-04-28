#!/usr/bin/env python3
"""stop-stale-check.py — Stop hook

Detects wiki pages whose referenced code was touched during the session but
whose `updated:` frontmatter date was NOT bumped. Emits a non-blocking
`additionalContext` message so Claude can fix it on the next turn (if any).

Heuristic: for every `codeToDocMapping` entry in config, if any code file
matching its pattern was written/edited in the session, check that the
corresponding doc's `updated:` value equals today's date. If not → flag.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root, normalise
from _lib.patterns import glob_to_regex, substitute
from _lib.transcript import collect_tool_writes


def session_writes(transcript_path: str) -> set[str]:
    """Backwards-compatible wrapper around `_lib.transcript.collect_tool_writes`.

    Returns the set of touched files normalised to absolute, forward-slash form
    (the historical shape this module has always emitted).
    """
    _, raw = collect_tool_writes(transcript_path)
    return {normalise(os.path.abspath(fp)) for fp in raw}


def updated_field(doc_path: str):
    try:
        with open(doc_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    m = re.search(r"^updated:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def run(payload: dict, project_root: str, cfg: dict, writes: int, files: set[str]) -> str | None:
    """Detect wiki pages with stale `updated:` against touched code. Returns context or None.

    `files` is the raw set from `_lib.transcript.collect_tool_writes`. We
    normalise locally — this lets the orchestrator share one parse with other
    Stop hooks that need the raw form.
    """
    opts = (cfg.get("hookEvents") or {}).get("stop") or {}
    if opts.get("staleCheck", True) is False:
        return None

    mappings = cfg.get("codeToDocMapping") or []
    if not mappings:
        return None

    touched = {normalise(os.path.abspath(fp)) for fp in files}
    if not touched:
        return None

    proj_norm = normalise(os.path.abspath(project_root)) + "/"
    today = datetime.date.today().isoformat()
    stale = []
    for entry in mappings:
        code_pattern = entry.get("codePattern")
        requires = entry.get("requiresDoc")
        if not code_pattern or not requires:
            continue
        regex = re.compile("^" + glob_to_regex(code_pattern) + "(.*)$")
        for f in touched:
            if not f.startswith(proj_norm):
                continue
            rel = f[len(proj_norm):]
            m = regex.match(rel)
            if not m:
                continue
            groups = m.groups()[:-1]
            alternatives = [a.strip() for a in requires.split(" OR ")]
            doc_rel = substitute(alternatives[0], groups)
            if "ANY" in doc_rel or "referencing" in doc_rel.lower():
                continue
            doc_path = os.path.join(project_root, cfg["root"], doc_rel)
            if not os.path.isfile(doc_path):
                continue
            u = updated_field(doc_path)
            if u != today:
                stale.append((cfg["root"] + "/" + doc_rel, u or "(missing)", os.path.relpath(f, project_root)))

    if not stale:
        return None

    lines = ["### Memex stale-check", "", "The following wiki pages reference code touched this session but were NOT updated:", ""]
    for doc, u, src in stale[:10]:
        lines.append(f"- **{doc}** (updated: `{u}`) — code touched: `{src}`")
    lines.append("")
    lines.append(f"Bump `updated:` to `{today}` and append to the page's changelog before closing out.")
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
