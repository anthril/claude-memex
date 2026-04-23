#!/usr/bin/env python3
"""frontmatter-check.py — PostToolUse hook (Write|Edit)

Validates YAML frontmatter on any file matching `frontmatter.appliesTo` glob
patterns under the ops root. Checks required fields + enum values from
`memex.config.json`.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_for_file
from _lib.frontmatter import validate
from _lib.paths import normalise


def block(msg: str) -> None:
    sys.stderr.write(f"[memex:frontmatter-check] BLOCKED: {msg}\n")
    sys.exit(2)


def matches_any(rel: str, patterns):
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
        # Support "**/foo" explicitly — fnmatch doesn't do `**` natively
        if pat.startswith("**/") and rel.endswith(pat[3:]):
            return True
        if pat.endswith("/**") and rel.startswith(pat[:-3]):
            return True
    return False


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

    ops_name = cfg["root"].rstrip("/").split("/")[-1]
    marker = f"/{ops_name}/"
    norm = normalise(file_path)
    idx = norm.rfind(marker)
    if idx == -1:
        sys.exit(0)
    rel = norm[idx + len(marker):]

    fm_cfg = cfg.get("frontmatter", {})
    applies_to = fm_cfg.get("appliesTo", [])
    if not matches_any(rel, applies_to):
        sys.exit(0)

    if not os.path.exists(file_path):
        sys.exit(0)

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        sys.exit(0)

    required = fm_cfg.get("required", [])
    enums = fm_cfg.get("enum", {})
    ok, msg = validate(content, required, enums)
    if not ok:
        block(
            f"{cfg['root']}/{rel} — {msg}. "
            f"See {cfg['root']}/.rules/documentation-rules.md."
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
