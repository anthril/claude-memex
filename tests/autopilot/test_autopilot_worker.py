"""Tests for the worker contract helpers (autopilot_worker.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
LIB = PLUGIN_ROOT / "hooks" / "scripts" / "_lib"
sys.path.insert(0, str(LIB))


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "MEMEX_AUTOPILOT_ROLE",
        "MEMEX_AUTOPILOT_RUN_ID",
        "MEMEX_AUTOPILOT_WORKER_ID",
        "CLAUDE_PROJECT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)


def _seed(tmp_path: Path, monkeypatch, task: dict) -> Path:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("MEMEX_AUTOPILOT_RUN_ID", "R1")
    monkeypatch.setenv("MEMEX_AUTOPILOT_WORKER_ID", "W1")
    wd = tmp_path / ".memex" / ".autopilot" / "runs" / "R1" / "W1"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "task.json").write_text(json.dumps(task), encoding="utf-8")
    return wd


def test_read_task_happy_path(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    task = {"kind": "oq-investigate", "target": "x", "runid": "R1", "worker_id": "W1", "specialist": "memex-planner"}
    _seed(tmp_path, monkeypatch, task)
    assert autopilot_worker.read_task() == task


def test_read_task_missing_env_raises(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    with pytest.raises(autopilot_worker.WorkerContractError):
        autopilot_worker.read_task()


def test_read_task_missing_file_raises(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("MEMEX_AUTOPILOT_RUN_ID", "R1")
    monkeypatch.setenv("MEMEX_AUTOPILOT_WORKER_ID", "W1")
    with pytest.raises(autopilot_worker.WorkerContractError, match="task.json missing"):
        autopilot_worker.read_task()


def test_read_task_malformed_raises(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("MEMEX_AUTOPILOT_RUN_ID", "R1")
    monkeypatch.setenv("MEMEX_AUTOPILOT_WORKER_ID", "W1")
    wd = tmp_path / ".memex" / ".autopilot" / "runs" / "R1" / "W1"
    wd.mkdir(parents=True)
    (wd / "task.json").write_text("not json {{{", encoding="utf-8")
    with pytest.raises(autopilot_worker.WorkerContractError, match="malformed"):
        autopilot_worker.read_task()


def test_read_task_missing_required_field_raises(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    _seed(tmp_path, monkeypatch, {"kind": "x"})
    with pytest.raises(autopilot_worker.WorkerContractError, match="missing required field"):
        autopilot_worker.read_task()


def test_write_report_appends_status_line(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    _seed(tmp_path, monkeypatch, {"kind": "x", "target": "y", "runid": "R1", "worker_id": "W1", "specialist": "z"})
    path = autopilot_worker.write_report("hello\nworld", "ok")
    text = path.read_text(encoding="utf-8")
    assert text.endswith("STATUS: ok\n")
    assert "hello\nworld" in text


def test_write_report_strips_existing_status_lines(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    _seed(tmp_path, monkeypatch, {"kind": "x", "target": "y", "runid": "R1", "worker_id": "W1", "specialist": "z"})
    path = autopilot_worker.write_report("body\n\nSTATUS: ok\n", "failed")
    text = path.read_text(encoding="utf-8")
    assert text.count("STATUS:") == 1
    assert text.endswith("STATUS: failed\n")
    assert "body" in text


def test_write_report_rejects_invalid_status(tmp_path: Path, monkeypatch) -> None:
    import autopilot_worker
    _seed(tmp_path, monkeypatch, {"kind": "x", "target": "y", "runid": "R1", "worker_id": "W1", "specialist": "z"})
    with pytest.raises(autopilot_worker.WorkerContractError):
        autopilot_worker.write_report("body", "winning")


def test_validate_status_line_recognises_each(tmp_path: Path) -> None:
    import autopilot_worker
    for s in ("ok", "failed", "needs-input"):
        assert autopilot_worker.validate_status_line(f"# x\n\nSTATUS: {s}\n") is True
    assert autopilot_worker.validate_status_line("# x\n\nSTATUS: invalid\n") is False
    assert autopilot_worker.validate_status_line("just text") is False
    assert autopilot_worker.validate_status_line("") is False


def test_path_allowlist_self_check(tmp_path: Path) -> None:
    import autopilot_worker
    assert autopilot_worker.is_path_allowed_for_worker(".memex/.autopilot/runs/R/W/REPORT.md")
    assert not autopilot_worker.is_path_allowed_for_worker(".memex/log.md")
    assert not autopilot_worker.is_path_allowed_for_worker("README.md")
