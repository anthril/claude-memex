"""Tests for the Memex Autopilot installer."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
INSTALL = PLUGIN_ROOT / "scripts" / "autopilot" / "installer.py"


def _seed_memex(tmp_path: Path) -> None:
    """Seed a minimal memex.config.json so installer --check passes."""
    (tmp_path / ".memex").mkdir(exist_ok=True)
    (tmp_path / "memex.config.json").write_text(
        json.dumps({"version": "1", "profile": "generic", "root": ".memex"}),
        encoding="utf-8",
    )


def _run(args: list[str], project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, str(INSTALL), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_check_passes_when_memex_initialised(tmp_path: Path) -> None:
    _seed_memex(tmp_path)
    proc = _run(["--check"], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK: all prerequisites present" in proc.stdout


def test_check_fails_when_memex_not_initialised(tmp_path: Path) -> None:
    proc = _run(["--check"], tmp_path)
    assert proc.returncode == 1
    assert "MISSING" in proc.stdout
    assert "memex not initialised" in proc.stdout


def test_apply_creates_state_store(tmp_path: Path) -> None:
    _seed_memex(tmp_path)
    proc = _run(["--apply"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    loop = tmp_path / ".memex" / ".autopilot"
    inbox = tmp_path / ".memex" / ".inbox"
    assert (loop / "state.json").exists()
    assert (loop / "BUDGET").exists()
    assert (loop / "history.jsonl").exists()
    assert (loop / "runs").is_dir()
    assert (loop / "locks").is_dir()
    assert (loop / "digests").is_dir()
    assert inbox.is_dir()
    assert (inbox / "quarantine").is_dir()
    state = json.loads((loop / "state.json").read_text(encoding="utf-8"))
    assert state["schema_version"] == 1
    assert state["config"]["max_sessions_per_day"] == 30
    budget = (loop / "BUDGET").read_text(encoding="utf-8").strip()
    assert int(budget) == 30


def test_apply_idempotent(tmp_path: Path) -> None:
    _seed_memex(tmp_path)
    proc1 = _run(["--apply"], tmp_path)
    state_path = tmp_path / ".memex" / ".autopilot" / "state.json"
    state1 = state_path.read_text(encoding="utf-8")
    proc2 = _run(["--apply"], tmp_path)
    assert proc2.returncode == 0
    assert state_path.read_text(encoding="utf-8") == state1
    out2 = json.loads(proc2.stdout)
    assert out2["state.json"] == "exists"


def test_self_test_passes_after_apply(tmp_path: Path) -> None:
    _seed_memex(tmp_path)
    _run(["--apply"], tmp_path)
    proc = _run(["--self-test"], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK: state load/save/append cycle" in proc.stdout


def test_no_args_prints_usage(tmp_path: Path) -> None:
    proc = _run([], tmp_path)
    assert proc.returncode == 2
    assert "specify at least one" in proc.stderr
