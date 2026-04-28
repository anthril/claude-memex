"""Tests for the autopilot-write-guard PreToolUse hook."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "scripts" / "autopilot-write-guard.py"


def _run(payload: dict, project_dir: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    for k in ("MEMEX_AUTOPILOT_ROLE", "MEMEX_AUTOPILOT_RUN_ID", "MEMEX_AUTOPILOT_WORKER_ID"):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_unrelated_tool_passes(tmp_path: Path) -> None:
    proc = _run({"tool_name": "Read", "tool_input": {"file_path": "anything.md"}}, tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_no_config_no_state_passes(tmp_path: Path) -> None:
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "foo.md")}},
        tmp_path,
    )
    assert proc.returncode == 0


def test_locked_path_exact_blocks(tmp_path: Path) -> None:
    (tmp_path / "memex.config.json").write_text(
        json.dumps({
            "version": "1", "profile": "generic", "root": ".memex",
            "autopilot": {"locked_paths": ["docs/charter.md"]},
        }),
        encoding="utf-8",
    )
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "docs" / "charter.md")}},
        tmp_path,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_locked_path_prefix_blocks(tmp_path: Path) -> None:
    (tmp_path / "memex.config.json").write_text(
        json.dumps({
            "version": "1", "profile": "generic", "root": ".memex",
            "autopilot": {"locked_paths": ["frozen/"]},
        }),
        encoding="utf-8",
    )
    proc = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "frozen" / "anything.md")}},
        tmp_path,
    )
    assert proc.returncode == 2


def test_unlocked_path_passes(tmp_path: Path) -> None:
    (tmp_path / "memex.config.json").write_text(
        json.dumps({
            "version": "1", "profile": "generic", "root": ".memex",
            "autopilot": {"locked_paths": ["docs/charter.md"]},
        }),
        encoding="utf-8",
    )
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "docs" / "guide.md")}},
        tmp_path,
    )
    assert proc.returncode == 0


def test_worker_sandbox_enforced(tmp_path: Path) -> None:
    """When MEMEX_AUTOPILOT_ROLE=worker, writes outside the worker sandbox are blocked."""
    (tmp_path / ".memex" / ".autopilot").mkdir(parents=True)
    (tmp_path / "memex.config.json").write_text(
        json.dumps({"version": "1", "profile": "generic", "root": ".memex"}),
        encoding="utf-8",
    )
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "outside.md")}},
        tmp_path,
        env_extra={
            "MEMEX_AUTOPILOT_ROLE": "worker",
            "MEMEX_AUTOPILOT_RUN_ID": "R1",
            "MEMEX_AUTOPILOT_WORKER_ID": "W1",
        },
    )
    assert proc.returncode == 2
    assert "worker-bounded" in proc.stdout


def test_worker_inside_sandbox_passes(tmp_path: Path) -> None:
    (tmp_path / ".memex" / ".autopilot").mkdir(parents=True)
    target = tmp_path / ".memex" / ".autopilot" / "runs" / "R1" / "W1" / "REPORT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        tmp_path,
        env_extra={
            "MEMEX_AUTOPILOT_ROLE": "worker",
            "MEMEX_AUTOPILOT_RUN_ID": "R1",
            "MEMEX_AUTOPILOT_WORKER_ID": "W1",
        },
    )
    assert proc.returncode == 0


def test_worker_in_shared_workspace_passes(tmp_path: Path) -> None:
    (tmp_path / ".memex" / ".autopilot").mkdir(parents=True)
    (tmp_path / "memex.config.json").write_text(
        json.dumps({
            "version": "1", "profile": "generic", "root": ".memex",
            "autopilot": {"shared_workspaces": ["audits/"]},
        }),
        encoding="utf-8",
    )
    proc = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "audits" / "x.md")}},
        tmp_path,
        env_extra={
            "MEMEX_AUTOPILOT_ROLE": "worker",
            "MEMEX_AUTOPILOT_RUN_ID": "R1",
            "MEMEX_AUTOPILOT_WORKER_ID": "W1",
        },
    )
    assert proc.returncode == 0
