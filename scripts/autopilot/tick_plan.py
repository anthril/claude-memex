"""PLAN phase — score backlog signals, pick top-K tasks, write task.json files.

Reads:
  * runs/<run-id>/perceive.json
  * state.json (for heuristics + max_workers_per_tick + exponential_backoff)
  * memex.config.json#/autopilot/task_kinds (optional override of default specialists)

Writes:
  * runs/<run-id>/<worker-id>/task.json (one per selected task)
  * runs/<run-id>/plan.json (scoring trace)

The autopilot ships no specialist agents. Default task-kind → specialist
mappings dispatch to Memex's built-in `memex-planner` subagent (for
investigation work). Host projects override via `autopilot.task_kinds`
in `memex.config.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


DEFAULT_TASK_KIND_DEFAULTS: dict[str, dict] = {
    "oq-investigate": {
        "specialist": "memex-planner",
        "max_tool_calls": 80,
        "max_tokens": 50000,
        "deadline_min": 45,
        "prompt_template": (
            "Investigate the open question at {target_path}. "
            "Walk linked specs, decisions, and candidate resolutions; emit a "
            "recommended resolution path and the smallest unblocking step. "
            "Do not author the resolution; only draft."
        ),
    },
    "owner-action-triage": {
        "specialist": "memex-planner",
        "max_tool_calls": 60,
        "max_tokens": 30000,
        "deadline_min": 30,
        "prompt_template": (
            "Triage the project-owner action at {target_path}. "
            "Read the action, gather context from linked wiki pages, and draft "
            "a status update + a recommended next step that the project owner "
            "(human) can review and approve."
        ),
    },
}


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_task_kind_config(root: Path) -> dict[str, dict]:
    """Return the merged DEFAULT + memex.config.json autopilot.task_kinds map."""
    config_path = root / "memex.config.json"
    merged: dict[str, dict] = {k: dict(v) for k, v in DEFAULT_TASK_KIND_DEFAULTS.items()}
    if not config_path.is_file():
        return merged
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return merged
    if not isinstance(cfg, dict):
        return merged
    overrides = ((cfg.get("autopilot") or {}).get("task_kinds")) or {}
    if not isinstance(overrides, dict):
        return merged
    for kind, override in overrides.items():
        if not isinstance(override, dict):
            continue
        merged.setdefault(kind, {})
        merged[kind].update(override)
    return merged


def deadline_pressure(target_close_date: str) -> float:
    """Higher score when deadline is closer. Range 0.0 (no deadline) to ~1.0."""
    if not target_close_date:
        return 0.5
    try:
        when = datetime.strptime(target_close_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_left = (when - datetime.now(timezone.utc)).total_seconds() / 86400.0
        if days_left < 0:
            return 1.2
        if days_left < 1:
            return 1.0
        if days_left < 7:
            return 0.9
        if days_left < 30:
            return 0.6
        return 0.4
    except Exception:
        return 0.5


def severity_weight(sev: str) -> float:
    return {"CRITICAL": 1.1, "HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}.get(
        (sev or "MEDIUM").upper(), 0.6
    )


def staleness(mtime: float) -> float:
    """Higher when last-touched a long time ago. Cap at 1.0."""
    if not mtime:
        return 0.5
    days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400.0
    if days < 1:
        return 0.2
    if days < 7:
        return 0.5
    if days < 30:
        return 0.8
    return 1.0


def is_under_backoff(slug: str, kind: str, backoff: dict) -> bool:
    entry = backoff.get(f"{kind}:{slug}")
    if not entry:
        return False
    try:
        when = datetime.fromisoformat(str(entry.get("next_eligible_at", "")).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) < when
    except Exception:
        return False


def short_worker_id(slug: str, kind: str) -> str:
    h = hashlib.sha1(f"{kind}:{slug}".encode("utf-8")).hexdigest()[:8]
    return f"w-{h}"


def build_task(
    kind: str,
    item: dict,
    run_id: str,
    task_kinds: dict[str, dict],
) -> dict:
    spec = task_kinds.get(kind) or {}
    specialist = spec.get("specialist", "memex-planner")
    max_tool_calls = int(spec.get("max_tool_calls", 60))
    max_tokens = int(spec.get("max_tokens", 30000))
    deadline_min = int(spec.get("deadline_min", 30))
    prompt_template = spec.get("prompt_template") or "Investigate {target_path}."

    slug = item["slug"]
    target_path = item.get("path") or slug
    prompt = prompt_template.format(target_path=target_path, slug=slug, target=slug)

    return {
        "kind": kind,
        "target": slug,
        "runid": run_id,
        "worker_id": short_worker_id(slug, kind),
        "specialist": specialist,
        "constraints": {
            "max_tool_calls": max_tool_calls,
            "max_tokens": max_tokens,
            "deadline_at": (datetime.now(timezone.utc) + timedelta(minutes=deadline_min)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "prompt_for_specialist": prompt,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = project_root()
    run_dir = root / ".memex" / ".autopilot" / "runs" / args.run_id
    perceive = json.loads((run_dir / "perceive.json").read_text(encoding="utf-8"))
    state = json.loads((root / ".memex" / ".autopilot" / "state.json").read_text(encoding="utf-8"))
    config = state.get("config") or {}
    max_workers = int(config.get("max_workers_per_tick", 3))
    backoff = state.get("heuristics", {}).get("exponential_backoff") or {}
    task_kinds = _load_task_kind_config(root)

    candidates: list[dict[str, Any]] = []

    for oq in perceive.get("oqs", []):
        slug = oq["slug"]
        if is_under_backoff(slug, "oq-investigate", backoff):
            continue
        score = (
            severity_weight(oq.get("severity"))
            * (0.5 + 0.5 * deadline_pressure(oq.get("target_close_date", "")))
            * (0.6 + 0.4 * staleness(oq.get("mtime", 0.0)))
        )
        candidates.append({
            "score": score,
            "kind": "oq-investigate",
            "data": oq,
        })

    for action in perceive.get("owner_actions", []):
        slug = action["slug"]
        if is_under_backoff(slug, "owner-action-triage", backoff):
            continue
        score = (
            severity_weight(action.get("severity"))
            * (0.4 + 0.5 * deadline_pressure(action.get("target_close_date", "")))
            * (0.5 + 0.4 * staleness(action.get("mtime", 0.0)))
        )
        candidates.append({
            "score": score * 0.85,
            "kind": "owner-action-triage",
            "data": action,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    selected: list[dict] = []
    seen_workers: set[str] = set()
    for c in candidates:
        if len(selected) >= max_workers:
            break
        task = build_task(c["kind"], c["data"], args.run_id, task_kinds)
        if task["worker_id"] in seen_workers:
            continue
        seen_workers.add(task["worker_id"])
        c["task"] = task
        selected.append(c)

    for c in selected:
        task = c["task"]
        worker_dir = run_dir / task["worker_id"]
        worker_dir.mkdir(parents=True, exist_ok=True)
        (worker_dir / "task.json").write_text(json.dumps(task, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    plan = {
        "ts": utcnow_iso(),
        "run_id": args.run_id,
        "max_workers": max_workers,
        "candidates_considered": len(candidates),
        "tasks_selected": [c["task"] for c in selected],
        "scoring_trace": [
            {"score": round(c["score"], 4), "kind": c["kind"], "target": c.get("task", {}).get("target")}
            for c in candidates[:10]
        ],
    }
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"PLAN: {len(selected)} tasks selected from {len(candidates)} candidates "
        f"(max_workers_per_tick={max_workers})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
