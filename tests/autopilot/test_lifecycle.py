"""Tests for the lifecycle helper (pause / resume / status / uninstall)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
LIFECYCLE = PLUGIN_ROOT / "scripts" / "autopilot" / "lifecycle.py"

DEFAULT_STATE = {
    "schema_version": 1,
    "last_tick_at": "2026-04-27T14:30:00Z",
    "next_tick_eta": "2026-04-27T16:00:00Z",
    "tick_count": 7,
    "in_flight": [],
    "goal_queue": [],
    "heuristics": {
        "task_kind_success_rate": {"oq-investigate": 0.91},
        "task_kind_mean_tokens": {},
        "exponential_backoff": {},
    },
    "config": {"max_workers_per_tick": 3, "max_sessions_per_day": 30},
}


def _seed(tmp_path: Path) -> None:
    loop = tmp_path / ".memex" / ".autopilot"
    loop.mkdir(parents=True, exist_ok=True)
    (loop / "state.json").write_text(json.dumps(DEFAULT_STATE), encoding="utf-8")
    (loop / "BUDGET").write_text("28\n", encoding="utf-8")
    (loop / "history.jsonl").write_text("", encoding="utf-8")
    inbox = tmp_path / ".memex" / ".inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "quarantine").mkdir(exist_ok=True)


def _run(cmd_args: list[str], project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, str(LIFECYCLE), *cmd_args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_pause_creates_file_and_logs_history(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["pause", "--reason", "release week"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    paused = tmp_path / ".memex" / ".autopilot" / "PAUSED"
    assert paused.exists()
    assert "release week" in paused.read_text(encoding="utf-8")
    history = (tmp_path / ".memex" / ".autopilot" / "history.jsonl").read_text(encoding="utf-8")
    assert '"phase": "paused"' in history
    assert "release week" in history


def test_pause_idempotent(tmp_path: Path) -> None:
    _seed(tmp_path)
    p1 = _run(["pause", "--reason", "first"], tmp_path)
    p2 = _run(["pause", "--reason", "second"], tmp_path)
    assert "Already paused" in p2.stdout
    paused = tmp_path / ".memex" / ".autopilot" / "PAUSED"
    assert "first" in paused.read_text(encoding="utf-8")
    assert "second" not in paused.read_text(encoding="utf-8")


def test_pause_when_not_installed(tmp_path: Path) -> None:
    proc = _run(["pause"], tmp_path)
    assert proc.returncode == 0
    assert "not installed" in proc.stdout


def test_resume_removes_paused_file(tmp_path: Path) -> None:
    _seed(tmp_path)
    _run(["pause", "--reason", "test"], tmp_path)
    proc = _run(["resume"], tmp_path)
    assert proc.returncode == 0
    paused = tmp_path / ".memex" / ".autopilot" / "PAUSED"
    assert not paused.exists()
    history = (tmp_path / ".memex" / ".autopilot" / "history.jsonl").read_text(encoding="utf-8")
    assert '"phase": "resumed"' in history


def test_resume_idempotent_when_not_paused(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["resume"], tmp_path)
    assert proc.returncode == 0
    assert "Already running" in proc.stdout


def test_status_basic(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["status"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "Memex Autopilot status" in proc.stdout
    assert "schema_version: 1" in proc.stdout
    assert "tick_count: 7" in proc.stdout
    assert "last_tick_at: 2026-04-27T14:30:00Z" in proc.stdout
    assert "PAUSED: no" in proc.stdout
    assert "budget remaining today: 28 sessions" in proc.stdout
    assert "oq-investigate=0.91" in proc.stdout


def test_status_shows_paused(tmp_path: Path) -> None:
    _seed(tmp_path)
    _run(["pause", "--reason", "manual test"], tmp_path)
    proc = _run(["status"], tmp_path)
    assert proc.returncode == 0
    assert "PAUSED: YES" in proc.stdout
    assert "manual test" in proc.stdout


def test_status_verbose_dumps_state(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["status", "--verbose"], tmp_path)
    assert proc.returncode == 0
    assert "## state.json" in proc.stdout
    assert "## last 5 history entries" in proc.stdout


def test_status_when_not_installed(tmp_path: Path) -> None:
    proc = _run(["status"], tmp_path)
    assert proc.returncode == 0
    assert "not installed" in proc.stdout


def test_uninstall_archives_state(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["uninstall"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / ".memex" / ".autopilot").is_dir()
    archives = list((tmp_path / ".memex").glob(".autopilot.archived-*"))
    assert len(archives) == 1
    assert (archives[0] / "state.json").is_file()


def test_uninstall_keep_state(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(["uninstall", "--keep-state"], tmp_path)
    assert proc.returncode == 0
    assert (tmp_path / ".memex" / ".autopilot").is_dir()
    paused = tmp_path / ".memex" / ".autopilot" / "PAUSED"
    assert paused.exists()
    assert "uninstall in progress" in paused.read_text(encoding="utf-8")
