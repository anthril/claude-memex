#!/usr/bin/env python3
"""path-guard.py — PreToolUse hook (Write|Edit)

Blocks writes under the ops root that violate:
  - kebab-case folder/file naming
  - dated folder format (configurable per root)
  - placement outside the permitted top-level allowlist

Reads rules from `memex.config.json`. Exits 0 to allow, 2 to block.
Silently passes for anything outside the ops root.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_for_file
from _lib.paths import (
    is_dated_folder,
    is_kebab_filename,
    is_kebab_segment,
    normalise,
)


def block(msg: str) -> None:
    sys.stderr.write(f"[memex:path-guard] BLOCKED: {msg}\n")
    sys.exit(2)


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
    if marker not in norm and not norm.endswith(f"/{ops_name}"):
        sys.exit(0)

    idx = norm.rfind(marker)
    rel = norm[idx + len(marker):]
    if not rel:
        sys.exit(0)

    parts = rel.split("/")
    allowed_top = set(cfg.get("allowedTopLevel", []))
    dated_paths = set(cfg.get("datedFolders", {}).get("paths", []))
    naming = cfg.get("naming", {})
    exceptions = set(naming.get("exceptions", []))
    # `asciiOnly` controls kebab validation. Default False → Unicode-friendly
    # (supports Japanese, Greek, Cyrillic, Arabic slugs). Set True to restrict
    # to ASCII `[a-z0-9]` for maximum portability / git-compatibility.
    ascii_only = bool(naming.get("asciiOnly", False))
    unicode_ok = not ascii_only

    if allowed_top and parts[0] not in allowed_top:
        block(
            f"'{parts[0]}' is not a permitted top-level folder under {cfg['root']}/. "
            f"Allowed: {sorted(allowed_top)}. "
            f"See {cfg['root']}/AGENTS.md and memex.config.json."
        )

    for seg in parts:
        if ":" in seg:
            block(
                f"Colon in path segment '{seg}' — invalid on Windows NTFS. "
                f"Use the dated format '{cfg['datedFolders'].get('format','DDMMYYYY-HHMM')}' without colons."
            )
        if " " in seg:
            block(f"Space in path segment '{seg}'. Use kebab-case.")

    # Dated folder enforcement: if parts[0] is a dated-path root, parts[1] must match the format
    rel_first = parts[0]
    if (rel_first in dated_paths and len(parts) >= 2
            and parts[1] != "README.md" and not is_dated_folder(parts[1])):
        block(
            f"Dated folder '{parts[1]}' under {cfg['root']}/{rel_first}/ must match "
            f"{cfg['datedFolders'].get('format','DDMMYYYY-HHMM')} (e.g. 22042026-1000)."
        )

    # Folder-segment kebab-case enforcement
    for seg in parts[:-1]:
        if seg in exceptions:
            continue
        if rel_first in dated_paths and is_dated_folder(seg):
            continue
        if seg.startswith("."):
            # top-level dotted folders (.rules, .open-questions, etc.) are whitelisted via allowedTopLevel
            continue
        if not is_kebab_segment(seg, unicode_ok=unicode_ok):
            mode_note = "ASCII-only" if ascii_only else "Unicode lowercase / caseless letters + digits"
            block(
                f"Folder segment '{seg}' is not kebab-case ({mode_note}). "
                f"Use lowercase letters, digits, and ASCII hyphens only; no uppercase, no spaces, "
                f"no consecutive or leading/trailing hyphens."
            )

    # Filename enforcement
    fname = parts[-1]
    if fname in exceptions or fname in {"README.md", "AGENTS.md", "CONVENTIONS.md", "CHANGELOG.md"}:
        sys.exit(0)
    if not is_kebab_filename(fname, unicode_ok=unicode_ok):
        mode_note = "ASCII-only" if ascii_only else "Unicode lowercase / caseless letters"
        block(
            f"Filename '{fname}' is not kebab-case ({mode_note}). "
            f"Use kebab-case.ext, optionally prefixed with a two-digit ordering prefix (e.g. 01-data-model.md). "
            f"Extensions must be ASCII lowercase."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
