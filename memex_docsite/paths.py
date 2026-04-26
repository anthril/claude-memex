"""Wiki-root discovery and path utilities.

Mirrors the discovery logic of `hooks/scripts/_lib/paths.py` so the docsite
sees the same wiki the hooks see.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_FILENAME = "memex.config.json"


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward from `start` (default: cwd) until `memex.config.json` is found.

    Raises FileNotFoundError if no config is found before reaching filesystem root.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_FILENAME).is_file():
            return candidate
    raise FileNotFoundError(
        f"no {CONFIG_FILENAME} found in {here} or any parent. "
        "Run `memex-docsite` from inside a memex-managed project."
    )


def load_raw_config(project_root: Path) -> dict:
    """Read `memex.config.json` at the given project root."""
    cfg_path = project_root / CONFIG_FILENAME
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def wiki_root(project_root: Path, raw_config: dict) -> Path:
    """Return the absolute path to the wiki root (default: `<project>/.memex`)."""
    root_name = raw_config.get("root", ".memex")
    return (project_root / root_name).resolve()


def is_inside(child: Path, parent: Path) -> bool:
    """Is `child` under `parent`? Both must be resolved absolute paths."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
