#!/usr/bin/env python3
"""stop-orchestrator.py — single Stop hook entry point.

Replaces four independently-registered Stop hooks (log-append, stale-check,
open-questions-check, project-owner-actions-check) with one. Walks the
session transcript ONCE via `_lib.transcript.collect_tool_writes` and
dispatches the parsed result to each module's `run()` function.

Each module is also still invokable directly (its `main()` is preserved) so
existing tests against the per-hook scripts keep working.

Output: a single `additionalContext` block — concatenation of every module
that returned context — preserving the multi-block shape Claude saw before.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root
from _lib.transcript import collect_tool_writes


# Order matters: log-append first (side-effect only), then context emitters in
# the order that produces the most readable concatenation.
HOOK_FILES = [
    "stop-log-append.py",
    "stop-stale-check.py",
    "stop-open-questions-check.py",
    "stop-project-owner-actions-check.py",
]


def _load_module(filename: str) -> types.ModuleType:
    """Load a sibling .py file as a module (filenames have hyphens)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, filename)
    mod_name = "_memex_stop_" + filename.replace("-", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    contexts: list[str] = []
    for filename in HOOK_FILES:
        try:
            mod = _load_module(filename)
        except Exception:
            continue
        run = getattr(mod, "run", None)
        if run is None:
            continue
        try:
            ctx = run(payload, project_root, cfg, writes, files)
        except Exception:
            ctx = None
        if ctx:
            contexts.append(ctx)

    if not contexts:
        sys.exit(0)

    out = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "\n\n".join(contexts),
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
