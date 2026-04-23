#!/usr/bin/env python3
"""readme-required.py — PreToolUse hook (Write)

Blocks Write into a new subfolder under a README-required tree unless the
first file written is README.md in that folder.

README-required trees are declared in `memex.config.json` under
`readmeRequired` as a list of glob-like patterns, e.g.:

    "readmeRequired": [
      "platform/features/*",
      "platform/systems/*",
      "entities/*"
    ]

Each pattern matches a slug directory. If the slug already contains
README.md on disk, the write is allowed; otherwise the write MUST be
the README.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_for_file
from _lib.paths import normalise


def block(msg: str) -> None:
    sys.stderr.write(f"[memex:readme-required] BLOCKED: {msg}\n")
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    if tool_name != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        sys.exit(0)

    cfg = load_config_for_file(file_path)
    if not cfg:
        sys.exit(0)

    patterns = cfg.get("readmeRequired") or []
    if not patterns:
        sys.exit(0)

    ops_name = cfg["root"].rstrip("/").split("/")[-1]
    marker = f"/{ops_name}/"
    norm = normalise(file_path)
    idx = norm.rfind(marker)
    if idx == -1:
        sys.exit(0)

    rel = norm[idx + len(marker):]
    parts = rel.split("/")
    if not parts:
        sys.exit(0)

    # Find a matching pattern. Pattern like "platform/features/*" matches when
    # the first N parts equal the literal prefix and part[N] is the slug.
    matched_depth = None
    matched_pattern = None
    for pat in patterns:
        pat_parts = pat.split("/")
        if len(pat_parts) < 2:
            continue
        prefix = pat_parts[:-1]
        last = pat_parts[-1]
        if last != "*":
            continue
        depth = len(prefix)
        if len(parts) > depth + 1 and parts[:depth] == prefix:
            matched_depth = depth
            matched_pattern = pat
            break

    if matched_depth is None:
        sys.exit(0)

    slug = parts[matched_depth]
    fname = parts[-1]

    # If the write IS the README, allow
    if len(parts) == matched_depth + 2 and fname == "README.md":
        sys.exit(0)

    # Otherwise, require README.md to already exist on disk in the slug folder
    project_root = cfg["__project_root"]
    ops_root_abs = os.path.normpath(os.path.join(project_root, cfg["root"]))
    slug_folder = os.path.join(ops_root_abs, *parts[:matched_depth + 1])
    readme_path = os.path.join(slug_folder, "README.md")

    if os.path.exists(readme_path):
        sys.exit(0)

    tree = "/".join(parts[:matched_depth])
    block(
        f"New subfolder {cfg['root']}/{tree}/{slug}/ has no README.md. "
        f"Create {cfg['root']}/{tree}/{slug}/README.md first (with full frontmatter) "
        f"before adding other files. Matched pattern: '{matched_pattern}'."
    )


if __name__ == "__main__":
    main()
