"""Integration tests for the tick phases (preflight, perceive, plan, integrate, learn)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = PLUGIN_ROOT / "scripts" / "autopilot"
PREFLIGHT = SCRIPT_DIR / "tick_preflight.py"
PERCEIVE = SCRIPT_DIR / "tick_perceive.py"
PLAN = SCRIPT_DIR / "tick_plan.py"
INTEGRATE = SCRIPT_DIR / "tick_integrate.py"
LEARN = SCRIPT_DIR / "tick_learn.py"

DEFAULT_STATE = {
    "schema_version": 1,
    "last_tick_at": None,
    "next_tick_eta": None,
    "tick_count": 0,
    "in_flight": [],
    "goal_queue": [],
    "heuristics": {
        "task_kind_success_rate": {},
        "task_kind_mean_tokens": {},
        "exponential_backoff": {},
    },
    "config": {
        "max_workers_per_tick": 3,
        "max_sessions_per_day": 30,
        "tick_deadline_min": 45,
        "max_attempts_per_task": 3,
    },
}


def _run(script: Path, args: list[str], project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, str(script), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _seed(tmp_path: Path) -> None:
    loop = tmp_path / ".memex" / ".autopilot"
    loop.mkdir(parents=True, exist_ok=True)
    (loop / "state.json").write_text(json.dumps(DEFAULT_STATE), encoding="utf-8")
    (loop / "BUDGET").write_text("30\n", encoding="utf-8")
    (loop / "history.jsonl").write_text("", encoding="utf-8")
    inbox = tmp_path / ".memex" / ".inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "quarantine").mkdir(exist_ok=True)


def _seed_oq(tmp_path: Path, slug: str, severity: str = "HIGH", date: str = "2026-04-30") -> None:
    oq_dir = tmp_path / ".memex" / ".open-questions"
    oq_dir.mkdir(parents=True, exist_ok=True)
    (oq_dir / f"{slug}.md").write_text(
        "# OQ\n\n## Ownership\n\n| field | value |\n|---|---|\n"
        f"| Severity | {severity} |\n| Target close date | {date} |\n",
        encoding="utf-8",
    )


def _seed_owner_action(tmp_path: Path, slug: str, severity: str = "HIGH", date: str = "2026-04-30") -> None:
    poa_dir = tmp_path / ".memex" / ".project-owner-actions"
    poa_dir.mkdir(parents=True, exist_ok=True)
    (poa_dir / f"{slug}.md").write_text(
        "# Action\n\n## Status\n\n| field | value |\n|---|---|\n"
        f"| Severity | {severity} |\n| Target close date | {date} |\n",
        encoding="utf-8",
    )


def test_preflight_blocks_when_paused(tmp_path: Path) -> None:
    _seed(tmp_path)
    (tmp_path / ".memex" / ".autopilot" / "PAUSED").write_text("test", encoding="utf-8")
    proc = _run(PREFLIGHT, [], tmp_path)
    assert proc.returncode == 0
    assert "BLOCKED" in proc.stdout
    assert "PAUSED" in proc.stdout


def test_preflight_blocks_when_not_installed(tmp_path: Path) -> None:
    proc = _run(PREFLIGHT, [], tmp_path)
    assert proc.returncode == 0
    assert "BLOCKED" in proc.stdout
    assert "not installed" in proc.stdout


def test_preflight_blocks_when_budget_exhausted(tmp_path: Path) -> None:
    _seed(tmp_path)
    (tmp_path / ".memex" / ".autopilot" / "BUDGET").write_text("0\n", encoding="utf-8")
    proc = _run(PREFLIGHT, [], tmp_path)
    assert proc.returncode == 0
    assert "BUDGET" in proc.stdout


def test_preflight_proceeds_when_clean(tmp_path: Path) -> None:
    _seed(tmp_path)
    proc = _run(PREFLIGHT, [], tmp_path)
    assert proc.returncode == 0
    assert "PROCEED" in proc.stdout


def _git_init(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True)


def test_perceive_writes_snapshot(tmp_path: Path) -> None:
    _seed(tmp_path)
    _seed_oq(tmp_path, "test-q")
    _seed_owner_action(tmp_path, "needs-signature")
    (tmp_path / ".memex" / ".autopilot" / "runs" / "R1").mkdir(parents=True)
    _git_init(tmp_path)
    proc = _run(PERCEIVE, ["--run-id", "R1"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    perceive = tmp_path / ".memex" / ".autopilot" / "runs" / "R1" / "perceive.json"
    assert perceive.is_file()
    data = json.loads(perceive.read_text(encoding="utf-8"))
    assert any(oq["slug"] == "test-q" for oq in data["oqs"])
    assert any(a["slug"] == "needs-signature" for a in data["owner_actions"])
    assert data["run_id"] == "R1"


def test_plan_picks_high_severity_oq(tmp_path: Path) -> None:
    _seed(tmp_path)
    _seed_oq(tmp_path, "high-q", severity="HIGH", date="2026-04-30")
    _seed_oq(tmp_path, "low-q", severity="LOW", date="2027-01-01")
    (tmp_path / ".memex" / ".autopilot" / "runs" / "R2").mkdir(parents=True)
    _git_init(tmp_path)
    p1 = _run(PERCEIVE, ["--run-id", "R2"], tmp_path)
    assert p1.returncode == 0, p1.stderr
    p2 = _run(PLAN, ["--run-id", "R2"], tmp_path)
    assert p2.returncode == 0, p2.stderr
    plan = json.loads((tmp_path / ".memex" / ".autopilot" / "runs" / "R2" / "plan.json").read_text(encoding="utf-8"))
    assert plan["tasks_selected"]
    selected_targets = [t["target"] for t in plan["tasks_selected"]]
    assert "high-q" in selected_targets
    # Specialist defaults to memex-planner.
    assert all(t["specialist"] == "memex-planner" for t in plan["tasks_selected"])


def test_plan_specialist_override_via_config(tmp_path: Path) -> None:
    _seed(tmp_path)
    _seed_oq(tmp_path, "the-q", severity="HIGH", date="2026-04-30")
    (tmp_path / "memex.config.json").write_text(
        json.dumps({
            "version": "1", "profile": "generic", "root": ".memex",
            "autopilot": {
                "task_kinds": {
                    "oq-investigate": {"specialist": "custom-specialist"}
                }
            },
        }),
        encoding="utf-8",
    )
    (tmp_path / ".memex" / ".autopilot" / "runs" / "R-CFG").mkdir(parents=True)
    _git_init(tmp_path)
    _run(PERCEIVE, ["--run-id", "R-CFG"], tmp_path)
    p2 = _run(PLAN, ["--run-id", "R-CFG"], tmp_path)
    assert p2.returncode == 0
    plan = json.loads((tmp_path / ".memex" / ".autopilot" / "runs" / "R-CFG" / "plan.json").read_text(encoding="utf-8"))
    assert plan["tasks_selected"][0]["specialist"] == "custom-specialist"


def test_integrate_routes_oq_to_inbox(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R3"
    wdir = rdir / "w-test"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "oq-investigate", "target": "my-oq", "runid": "R3", "worker_id": "w-test", "specialist": "x"}),
        encoding="utf-8",
    )
    (wdir / "REPORT.md").write_text("# Report\n\nSpecialist said yes.\n\nSTATUS: ok\n", encoding="utf-8")
    proc = _run(INTEGRATE, ["--run-id", "R3"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    inbox_file = tmp_path / ".memex" / ".inbox" / "R3" / "oq-resolution-my-oq.md"
    assert inbox_file.is_file()
    inbox_index = tmp_path / ".memex" / ".inbox" / "INBOX.md"
    assert "my-oq" in inbox_index.read_text(encoding="utf-8")
    summary = (rdir / "SUMMARY.md").read_text(encoding="utf-8")
    assert "STATUS: ok" in summary


def test_integrate_routes_owner_action(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R3b"
    wdir = rdir / "w-action"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "owner-action-triage", "target": "needs-signature", "runid": "R3b", "worker_id": "w-action", "specialist": "x"}),
        encoding="utf-8",
    )
    (wdir / "REPORT.md").write_text("# Report\n\nNeeds owner.\n\nSTATUS: needs-input\n", encoding="utf-8")
    proc = _run(INTEGRATE, ["--run-id", "R3b"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    inbox_file = tmp_path / ".memex" / ".inbox" / "R3b" / "owner-action-triage-needs-signature.md"
    assert inbox_file.is_file()


def test_integrate_quarantines_failed(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R4"
    wdir = rdir / "w-bad"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "oq-investigate", "target": "x", "runid": "R4", "worker_id": "w-bad", "specialist": "y"}),
        encoding="utf-8",
    )
    (wdir / "REPORT.md").write_text("# Report\n\nThings broke.\n\nSTATUS: failed\n", encoding="utf-8")
    proc = _run(INTEGRATE, ["--run-id", "R4"], tmp_path)
    assert proc.returncode == 0
    qdir = tmp_path / ".memex" / ".inbox" / "quarantine" / "R4"
    assert (qdir / "w-bad.md").is_file()


def test_integrate_handles_missing_report(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R5"
    wdir = rdir / "w-missing"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "oq-investigate", "target": "x", "runid": "R5", "worker_id": "w-missing", "specialist": "y"}),
        encoding="utf-8",
    )
    proc = _run(INTEGRATE, ["--run-id", "R5"], tmp_path)
    assert proc.returncode == 0
    summary = (rdir / "SUMMARY.md").read_text(encoding="utf-8")
    assert "no REPORT.md" in summary


def test_learn_increments_tick_count_and_appends_history(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R6"
    wdir = rdir / "w-learn"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "oq-investigate", "target": "x", "runid": "R6", "worker_id": "w-learn", "specialist": "y"}),
        encoding="utf-8",
    )
    (wdir / "REPORT.md").write_text("# OK\nSTATUS: ok\n", encoding="utf-8")
    (rdir / "SUMMARY.md").write_text("- ok: 1\n- failed: 0\n- needs-input: 0\n- missing: 0\n", encoding="utf-8")
    proc = _run(LEARN, ["--run-id", "R6", "--next-eta-min", "90"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    state = json.loads((tmp_path / ".memex" / ".autopilot" / "state.json").read_text(encoding="utf-8"))
    assert state["tick_count"] == 1
    assert state["last_tick_at"] is not None
    history = (tmp_path / ".memex" / ".autopilot" / "history.jsonl").read_text(encoding="utf-8")
    assert "tick_complete" in history
    assert state["heuristics"]["task_kind_success_rate"]["oq-investigate"] > 0.5


def test_learn_bumps_backoff_on_failure(tmp_path: Path) -> None:
    _seed(tmp_path)
    rdir = tmp_path / ".memex" / ".autopilot" / "runs" / "R7"
    wdir = rdir / "w-fail"
    wdir.mkdir(parents=True)
    (wdir / "task.json").write_text(
        json.dumps({"kind": "oq-investigate", "target": "fails", "runid": "R7", "worker_id": "w-fail", "specialist": "y"}),
        encoding="utf-8",
    )
    (wdir / "REPORT.md").write_text("STATUS: failed\n", encoding="utf-8")
    (rdir / "SUMMARY.md").write_text("- ok: 0\n- failed: 1\n- needs-input: 0\n- missing: 0\n", encoding="utf-8")
    proc = _run(LEARN, ["--run-id", "R7"], tmp_path)
    assert proc.returncode == 0
    state = json.loads((tmp_path / ".memex" / ".autopilot" / "state.json").read_text(encoding="utf-8"))
    assert "oq-investigate:fails" in state["heuristics"]["exponential_backoff"]
    assert state["heuristics"]["exponential_backoff"]["oq-investigate:fails"]["failures"] == 1
