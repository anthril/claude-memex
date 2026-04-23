"""Glob-to-regex conversion + template substitution.

Previously copy-pasted across `doc-required.py`, `ingest-doc-link.py`, and
`stop-stale-check.py`. Centralised here so pattern semantics evolve in one
place.

The glob syntax Memex uses in `memex.config.json#/codeToDocMapping`:

    src/features/*/          →  src/features/([^/]+)/
    supabase/migrations/*.sql →  supabase/migrations/([^/]+)\\.sql
    deep/**/file.ts          →  deep/(.+)/file\\.ts

`*`  — matches any segment (no `/`)
`**` — matches any number of segments (including `/`)

After matching against a target path, use `substitute(template, groups)` to
expand `{1}`, `{2}`, … placeholders in `requiresDoc` strings.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

_META = set(".+?^$()[]{}|\\")


def glob_to_regex(pattern: str) -> str:
    """Convert a simple path glob (see module docstring) into a regex with
    capture groups. Not anchored — caller wraps with ^/$ as needed.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                out.append("(.+)")
                i += 2
            else:
                out.append("([^/]+)")
                i += 1
        elif c in _META:
            out.append("\\" + c)
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def substitute(template: str, groups: Sequence[str]) -> str:
    """Replace `{1}`, `{2}`, … in `template` with the matching element from
    `groups` (1-indexed). Leaves `{N}` unchanged if N is out of range.
    """
    def repl(m: re.Match) -> str:
        idx = int(m.group(1))
        return groups[idx - 1] if 1 <= idx <= len(groups) else m.group(0)
    return re.sub(r"\{(\d+)\}", repl, template)
