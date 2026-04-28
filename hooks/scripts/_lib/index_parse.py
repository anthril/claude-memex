"""Parse index.md into sections + the link targets each section references.

`index.md` structure by convention:

    # Index

    ## Entities
    - [Foo](entities/foo/README.md)
    - [Bar](entities/bar/README.md)

    ## Concepts
    *No concepts yet.*

    ## Recent Activity
    ...

This module turns that into:

    {
      "Entities": {"entities/foo/README.md", "entities/bar/README.md"},
      "Concepts": set(),
      "Recent Activity": set(),
    }

Handles wikilinks (`[[slug]]`) and frontmatter-style titles too. Designed to
be liberal in what it accepts — the index format is author-controlled.
"""
from __future__ import annotations

import json
import os
import re

# `[text](target)` where target is a relative path (not http/https/mailto)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(((?!https?://|mailto:|#)[^\)\s]+)\)")
# `[[slug]]` wikilinks
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
# Top-level heading and section heading
H1_RE = re.compile(r"^#\s+")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def parse_index(content: str) -> dict[str, set[str]]:
    """Parse index content into {section_name: set_of_link_targets}."""
    sections: dict[str, set[str]] = {}
    current: str | None = None
    for line in content.splitlines():
        m = H2_RE.match(line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, set())
            continue
        if current is None:
            continue
        for link_m in MD_LINK_RE.finditer(line):
            sections[current].add(link_m.group(2).strip())
        for wl_m in WIKILINK_RE.finditer(line):
            sections[current].add(wl_m.group(1).strip())
    return sections


def parse_index_file_cached(index_path: str, ops_root: str) -> dict[str, set[str]]:
    """Parse `index_path`, reusing a cached parse keyed by file mtime.

    Cache lives at `<ops_root>/.state/index-parse.json`. On a hit (mtime matches)
    we deserialize the cached parse instead of re-reading + re-regexing the file.
    `index-update.py` fires on every Write/Edit of a .md file under the wiki,
    so a writing-heavy session would otherwise re-parse the same index N times.

    The cache invalidates automatically when `index.md` changes (Claude bumps
    it after adding a new entry, which sets a new mtime, which invalidates here).

    Failures fall back to an uncached parse — never raises.
    """
    try:
        mtime = os.path.getmtime(index_path)
    except OSError:
        return {}

    state_dir = os.path.join(ops_root.rstrip("/").rstrip("\\"), ".state")
    cache_path = os.path.join(state_dir, "index-parse.json")

    try:
        with open(cache_path, encoding="utf-8") as fh:
            cached = json.load(fh)
        if (
            isinstance(cached, dict)
            and cached.get("path") == index_path
            and float(cached.get("mtime", -1)) == mtime
            and isinstance(cached.get("sections"), dict)
        ):
            return {name: set(refs) for name, refs in cached["sections"].items()}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    try:
        with open(index_path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return {}
    sections = parse_index(content)

    try:
        os.makedirs(state_dir, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "path": index_path,
                    "mtime": mtime,
                    "sections": {name: sorted(refs) for name, refs in sections.items()},
                },
                fh,
            )
    except OSError:
        pass

    return sections


def flatten(sections: dict[str, set[str]]) -> set[str]:
    """All link targets across all sections."""
    out: set[str] = set()
    for refs in sections.values():
        out |= refs
    return out


def contains_reference(sections: dict[str, set[str]], rel_path: str, slug: str) -> bool:
    """Is this page referenced by `rel_path` or `slug`, in any section?"""
    all_refs = flatten(sections)
    if rel_path in all_refs:
        return True
    # Also accept if any reference ends with the rel_path (e.g. ref is an absolute-ish
    # path prefixed by the root, or ref and rel are just the same file via different
    # relative base).
    for ref in all_refs:
        if ref.endswith("/" + rel_path) or ref == rel_path:
            return True
    # Wikilink slug match
    return bool(slug and slug in all_refs)


def suggest_section(
    sections: dict[str, set[str]],
    rel_path: str,
    page_type: str | None = None,
) -> str | None:
    """Best-effort guess at which section this page should slot into.

    Strategy:
      1. If `page_type` matches a section name (case-insensitive, singular→plural),
         use that.
      2. If the first folder segment of `rel_path` matches a section name, use it.
      3. Otherwise None → caller can fall back to generic suggestion.
    """
    if not sections:
        return None
    section_names = list(sections.keys())

    def match(candidate: str) -> str | None:
        if not candidate:
            return None
        cand_lower = candidate.lower()
        for name in section_names:
            nl = name.lower()
            if nl == cand_lower or nl == cand_lower + "s" or nl == cand_lower + "es":
                return name
            if nl.rstrip("s") == cand_lower:
                return name
        return None

    if page_type:
        hit = match(page_type)
        if hit:
            return hit

    first_segment = rel_path.split("/", 1)[0]
    hit = match(first_segment)
    if hit:
        return hit

    return None
