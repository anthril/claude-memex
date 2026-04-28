#!/usr/bin/env python3
"""PreToolUse write-guard hook for Memex Autopilot.

Hard-blocks Write/Edit attempts against the project's locked-immutable
paths and (when running inside a worker session) confines writes to
that worker's sandbox plus any shared workspaces declared in config.

This is the central trust enforcer for the multi-agent loop: it must
fire before the tool runs and cannot be bypassed from inside an agent
prompt.

Behaviour:
  * Reads PreToolUse JSON payload from stdin.
  * Resolves ``tool_input.file_path`` to an absolute path; relative
    paths resolve against ``CLAUDE_PROJECT_DIR``.
  * Path denylist (always enforced) — read from
    ``memex.config.json#/autopilot/locked_paths``. Each entry is
    either an exact relative posix path or a prefix ending in ``/``.
  * Worker-bounded enforcement — when ``MEMEX_AUTOPILOT_ROLE=worker``
    is set, writes are confined to the run-and-worker sandbox plus any
    shared workspaces declared in
    ``memex.config.json#/autopilot/shared_workspaces``.
  * Coordinator / human sessions (any other role value, or none): only
    the denylist applies.
  * Block: stderr one-line reason; stdout JSON
    ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny", "permissionDecisionReason": ...}}``;
    exit code 2.
  * Allow: exit 0, no stdout.
  * No-op early exit when ``.memex/.autopilot/`` does not exist
    (autopilot not installed) — except for the denylist, which is
    *always* enforced if config declares it.
  * Fail-open: malformed stdin / unexpected error -> exit 0 with a
    stderr warning. Hooks must never break the user's flow.

Stdlib only; Python 3.10+.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path, PurePosixPath

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def _load_autopilot_config(root: Path) -> dict:
    """Read memex.config.json#/autopilot. Empty dict on any read error."""
    config_path = root / "memex.config.json"
    if not config_path.is_file():
        return {}
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(cfg, dict):
        return {}
    ap = cfg.get("autopilot")
    if not isinstance(ap, dict):
        return {}
    return ap


def _norm_prefixes(items: list) -> tuple[list[str], list[str]]:
    """Split a list of strings into (exact-files, prefixes).

    Convention: an entry ending with `/` is treated as a prefix; otherwise
    it's an exact relative posix path match.
    """
    exact: list[str] = []
    prefixes: list[str] = []
    for raw in items or []:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue
        s = s.replace("\\", "/").lstrip("./")
        if s.endswith("/"):
            prefixes.append(s)
        else:
            exact.append(s)
    return exact, prefixes


def to_posix_relative(target: Path, root: Path) -> str | None:
    try:
        rel = target.resolve().relative_to(root)
    except ValueError:
        return None
    return PurePosixPath(rel).as_posix()


def emit_deny(reason: str) -> int:
    sys.stderr.write(f"[autopilot-write-guard] DENY: {reason}\n")
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(payload))
    return 2


def check_denylist(rel_posix: str, exact: list[str], prefixes: list[str]) -> str | None:
    if rel_posix in exact:
        return (
            f"locked-immutable: {rel_posix} is on the autopilot.locked_paths denylist; "
            "edits require human review (remove the entry from memex.config.json or supersede via a new file)."
        )
    for pref in prefixes:
        if rel_posix.startswith(pref):
            return (
                f"locked-immutable: {rel_posix} falls under autopilot.locked_paths prefix {pref!r}; "
                "edits require human review."
            )
    return None


def check_worker_sandbox(
    rel_posix: str,
    run_id: str,
    worker_id: str,
    shared_prefixes: list[str],
) -> str | None:
    worker_prefix = f".memex/.autopilot/runs/{run_id}/{worker_id}/"
    if rel_posix.startswith(worker_prefix):
        return None
    if any(rel_posix.startswith(p) for p in shared_prefixes):
        return None
    return (
        f"worker-bounded: {rel_posix} is outside the worker sandbox "
        f"({worker_prefix}) and the configured autopilot.shared_workspaces."
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("payload is not a JSON object")

        tool = str(payload.get("tool_name") or "")
        if tool not in {"Write", "Edit"}:
            return 0

        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0

        raw_path = tool_input.get("file_path") or ""
        if not isinstance(raw_path, str) or not raw_path.strip():
            return 0

        root = project_root()
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = root / raw_path

        ap_cfg = _load_autopilot_config(root)
        locked_exact, locked_prefixes = _norm_prefixes(ap_cfg.get("locked_paths") or [])
        _, shared_prefixes = _norm_prefixes(ap_cfg.get("shared_workspaces") or [])

        loop_dir = root / ".memex" / ".autopilot"
        autopilot_installed = loop_dir.is_dir()

        rel_posix = to_posix_relative(candidate, root)
        if rel_posix is None:
            role = os.environ.get("MEMEX_AUTOPILOT_ROLE", "")
            if role == "worker":
                return emit_deny(
                    f"worker-bounded: {raw_path} resolves outside the project root."
                )
            return 0

        deny = check_denylist(rel_posix, locked_exact, locked_prefixes)
        if deny:
            return emit_deny(deny)

        if not autopilot_installed:
            return 0

        if os.environ.get("MEMEX_AUTOPILOT_ROLE", "") == "worker":
            run_id = os.environ.get("MEMEX_AUTOPILOT_RUN_ID", "").strip()
            worker_id = os.environ.get("MEMEX_AUTOPILOT_WORKER_ID", "").strip()
            if not run_id or not worker_id:
                return emit_deny(
                    "worker-bounded: MEMEX_AUTOPILOT_ROLE=worker but "
                    "MEMEX_AUTOPILOT_RUN_ID / MEMEX_AUTOPILOT_WORKER_ID is unset."
                )
            sandbox_deny = check_worker_sandbox(rel_posix, run_id, worker_id, shared_prefixes)
            if sandbox_deny:
                return emit_deny(sandbox_deny)

        return 0

    except Exception as exc:
        sys.stderr.write(f"[autopilot-write-guard] WARN: hook bypassed ({exc!r})\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
