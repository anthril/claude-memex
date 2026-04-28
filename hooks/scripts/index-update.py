#!/usr/bin/env python3
"""index-update.py — PostToolUse hook (Write|Edit)

Non-blocking nudge: after a new page lands under the wiki root, parse
`index.md` section-by-section and check whether the page is referenced. If
not, emit `additionalContext` suggesting Claude add the entry — and, where
possible, which section to put it under.

This is smarter than a plain string match: it respects section boundaries,
understands wikilinks + markdown links, and uses the page's frontmatter
`type:` field to suggest the right section.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_for_file
from _lib.frontmatter import parse as parse_frontmatter
from _lib.index_parse import contains_reference, parse_index_file_cached, suggest_section
from _lib.paths import normalise


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path or not file_path.endswith(".md"):
        sys.exit(0)
    if not os.path.exists(file_path):
        sys.exit(0)

    cfg = load_config_for_file(file_path)
    if not cfg:
        sys.exit(0)

    ops_name = cfg["root"].rstrip("/").split("/")[-1]
    marker = f"/{ops_name}/"
    norm = normalise(file_path)
    idx = norm.rfind(marker)
    if idx == -1:
        sys.exit(0)

    rel = norm[idx + len(marker):]

    # Don't nudge for structural files or plugin-state files
    if rel in ("index.md", "log.md", "AGENTS.md", "README.md"):
        sys.exit(0)
    if rel.startswith(".state/") or rel.startswith(".rules/") or rel.startswith(".open-questions/"):
        sys.exit(0)

    index_rel = cfg.get("index", {}).get("path", "index.md")
    ops_root = os.path.join(cfg["__project_root"], cfg["root"])
    index_path = os.path.join(ops_root, index_rel)
    if not os.path.isfile(index_path):
        sys.exit(0)

    sections = parse_index_file_cached(index_path, ops_root)

    try:
        with open(file_path, encoding="utf-8") as f:
            page_content = f.read()
    except Exception:
        sys.exit(0)

    fm = parse_frontmatter(page_content) or {}
    slug = fm.get("slug") or os.path.splitext(os.path.basename(rel))[0]
    page_type = fm.get("type")

    if contains_reference(sections, rel, slug):
        sys.exit(0)

    suggested = suggest_section(sections, rel, page_type)
    suggestion_line = (
        f"Under **## {suggested}** seems right." if suggested else
        "Pick the section that best fits this page's `type:`."
    )

    title = fm.get("title") or slug
    link_hint = f"  - [{title}]({rel})"
    msg = (
        f"### Memex index reminder\n\n"
        f"`{cfg['root']}/{rel}` was just written/edited but isn't referenced from `{cfg['root']}/{index_rel}`. "
        f"{suggestion_line}\n\n"
        f"Suggested entry:\n\n```markdown\n{link_hint}\n```"
    )

    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
