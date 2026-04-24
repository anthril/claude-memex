#!/usr/bin/env python3
"""doc-required.py — PreToolUse hook (Write|Edit)

Enforces that code paths declared in `codeToDocMapping` (in `memex.config.json`)
have a linked wiki page before new code lands. Each mapping entry declares:

  - codePattern: a glob-ish path pattern with `*` capture groups, matched
    against paths relative to the project root
  - requiresDoc: a relative doc path with `{1}`, `{2}`, ... substitution
    from the matched groups
  - severity: "warn" | "block" | "warn-then-block"
  - stateKey: optional label for per-session state tracking

If the code pattern matches a write target, we check the required doc exists.
Missing doc → warn, block, or warn-then-block per severity.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import state as state_mod
from _lib.config import load_config_for_file
from _lib.paths import normalise
from _lib.patterns import glob_to_regex, substitute


def block(msg: str) -> None:
    sys.stderr.write(f"[memex:doc-required] BLOCKED: {msg}\n")
    sys.exit(2)


def warn(msg: str) -> None:
    sys.stderr.write(f"[memex:doc-required] WARNING: {msg}\n")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        sys.exit(0)

    cfg = load_config_for_file(file_path)
    if not cfg:
        sys.exit(0)

    mappings = cfg.get("codeToDocMapping") or []
    if not mappings:
        sys.exit(0)

    project_root = cfg["__project_root"]
    norm_abs = normalise(os.path.abspath(file_path))
    norm_root = normalise(os.path.abspath(project_root))
    if not norm_abs.startswith(norm_root + "/"):
        sys.exit(0)
    rel = norm_abs[len(norm_root) + 1:]

    ops_root_abs = os.path.normpath(os.path.join(project_root, cfg["root"]))

    for entry in mappings:
        code_pattern = entry.get("codePattern")
        requires_doc = entry.get("requiresDoc")
        if not code_pattern or not requires_doc:
            continue
        regex = "^" + glob_to_regex(code_pattern) + "(.*)$"
        m = re.match(regex, rel)
        if not m:
            continue

        groups = m.groups()[:-1]  # drop the trailing wildcard group
        # If `requiresDoc` contains " OR ", accept any alternative
        alternatives = [a.strip() for a in requires_doc.split(" OR ")]
        for alt in alternatives:
            doc_rel = substitute(alt, groups)
            # Alternative can reference the ops root relatively (e.g. "platform/features/{1}/README.md")
            candidate = os.path.join(ops_root_abs, doc_rel)
            if os.path.exists(candidate):
                sys.exit(0)
            # Also accept if `doc_rel` is actually a fallback phrase like "ANY .md referencing..."
            if "ANY" in alt or "referencing" in alt.lower():
                # Too fuzzy to verify here — defer to ingest-doc-link.py for those cases.
                sys.exit(0)

        severity = entry.get("severity", "warn-then-block")
        state_key = entry.get("stateKey") or "doc-required"
        slug = groups[0] if groups else rel
        target_display = substitute(alternatives[0], groups)

        msg = (
            f"No documentation found for code in '{code_pattern}' (slug '{slug}'). "
            f"Create {cfg['root']}/{target_display} with full frontmatter before adding code."
        )

        if severity == "block":
            block(msg)
        if severity == "warn":
            warn(msg)
            sys.exit(0)
        # warn-then-block (default)
        count = state_mod.bump(project_root, cfg["root"], state_key, slug)
        if count >= 2:
            block(msg)
        warn(msg + " (first offence — next edit for this slug will be blocked)")
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
