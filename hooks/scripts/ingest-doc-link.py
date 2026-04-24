#!/usr/bin/env python3
"""ingest-doc-link.py — PreToolUse hook (Write)

Enforces that "ingestible" artifacts (declared in `codeToDocMapping` with
`severity: block` and typically a distinct file type like .sql migrations)
either:
  (a) carry a header comment referencing a doc under the wiki root, e.g.
      `-- Doc: .memex/platform/systems/users/README.md`, OR
  (b) have their slug / filename referenced somewhere in the wiki root.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_for_file
from _lib.paths import normalise
from _lib.patterns import glob_to_regex


def block(msg: str) -> None:
    sys.stderr.write(f"[memex:ingest-doc-link] BLOCKED: {msg}\n")
    sys.exit(2)


def scan_for_reference(ops_root_abs: str, needles) -> bool:
    if not os.path.isdir(ops_root_abs):
        return False
    for root, _dirs, files in os.walk(ops_root_abs):
        for f in files:
            if not f.endswith(".md"):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, encoding="utf-8") as fh:
                    content = fh.read()
            except Exception:
                continue
            for needle in needles:
                if needle and needle in content:
                    return True
    return False


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

    mappings = cfg.get("codeToDocMapping") or []
    block_entries = [m for m in mappings if m.get("severity") == "block"]
    if not block_entries:
        sys.exit(0)

    project_root = cfg["__project_root"]
    norm_abs = normalise(os.path.abspath(file_path))
    norm_root = normalise(os.path.abspath(project_root))
    if not norm_abs.startswith(norm_root + "/"):
        sys.exit(0)
    rel = norm_abs[len(norm_root) + 1:]

    # Let edits-through on existing files
    if os.path.exists(file_path):
        sys.exit(0)

    ops_root_abs = os.path.normpath(os.path.join(project_root, cfg["root"]))
    content = tool_input.get("content") or ""
    doc_header_re = re.compile(
        r"(--|//|\#|/\*)\s*Doc:\s*" + re.escape(cfg["root"]) + r"/[^\s\n*]+"
    )

    for entry in block_entries:
        code_pattern = entry.get("codePattern")
        if not code_pattern:
            continue
        regex = "^" + glob_to_regex(code_pattern) + "(.*)$"
        m = re.match(regex, rel)
        if not m:
            continue

        # Accept doc-header form
        if doc_header_re.search(content):
            sys.exit(0)

        # Otherwise, require the filename or derived slug to appear in any ops-root .md
        basename = os.path.basename(rel)
        name_without_ext = os.path.splitext(basename)[0]
        # derive a slug by stripping leading timestamp-like prefixes
        slug_match = re.match(r"(?:\d+_)?([a-z0-9][a-z0-9_\-]+)$", name_without_ext)
        slug = slug_match.group(1) if slug_match else name_without_ext

        if scan_for_reference(ops_root_abs, [slug, basename]):
            sys.exit(0)

        block(
            f"New ingestible artifact '{basename}' has no linked doc. "
            f"Either (a) reference '{slug}' or '{basename}' from a {cfg['root']}/ markdown file, or "
            f"(b) add a header comment of the form `-- Doc: {cfg['root']}/<path>.md` "
            f"(or `# Doc: ...` for scripts, `// Doc: ...` for JS) to the file. "
            f"Pattern matched: '{code_pattern}'."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
