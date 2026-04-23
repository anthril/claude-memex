"""Per-session warn-then-block state.

Stored under `.memex/.state/<name>.json` in the target project. Hooks that
track "first offence warn, second offence block" use this.
"""
from __future__ import annotations

import json
import os
from typing import Any


def state_dir(project_root: str, ops_root: str) -> str:
    return os.path.join(project_root, ops_root, ".state")


def load(project_root: str, ops_root: str, name: str) -> dict[str, Any]:
    path = os.path.join(state_dir(project_root, ops_root), f"{name}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(project_root: str, ops_root: str, name: str, data: dict[str, Any]) -> None:
    d = state_dir(project_root, ops_root)
    try:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        # State is opportunistic — never block a tool call on state-write failure.
        pass


def bump(project_root: str, ops_root: str, name: str, key: str) -> int:
    """Increment a counter and return its new value."""
    data = load(project_root, ops_root, name)
    data[key] = int(data.get(key, 0)) + 1
    save(project_root, ops_root, name, data)
    return data[key]
