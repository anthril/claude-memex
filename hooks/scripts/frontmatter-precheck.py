#!/usr/bin/env python3
"""frontmatter-precheck.py — PreToolUse hook (Edit)

Optional belt-and-braces check that runs BEFORE an Edit to a wiki page with
required frontmatter. If the current on-disk content already fails validation
(because something wrote it outside our toolchain), warn so the Edit doesn't
compound an already-broken page.

Non-blocking. Complements the PostToolUse `frontmatter-check.py` which IS
blocking.
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


def warn(msg: str) -> None:
    sys.stderr.write(f"[memex:frontmatter-precheck] WARNING: {msg}\n")


def matches_any(rel: str, patterns):
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
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

    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    if tool_name != "Edit":
        sys.exit(0)

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path or not os.path.exists(file_path):
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
    applies = fm_cfg.get("appliesTo", [])
    if not matches_any(rel, applies):
        sys.exit(0)

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        sys.exit(0)

    ok, msg = validate(content, fm_cfg.get("required", []), fm_cfg.get("enum", {}))
    if not ok:
        warn(f"Pre-edit check on {cfg['root']}/{rel}: {msg}. The Edit will proceed; the PostToolUse check will block if the final state is still invalid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
