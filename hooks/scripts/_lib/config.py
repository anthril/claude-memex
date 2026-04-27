"""Load and validate `memex.config.json`.

Every hook reads the project's config. This module centralises lookup and
provides sensible defaults so a minimal config still produces working
enforcement.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .paths import find_project_root

DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1",
    "profile": "generic",
    "root": ".memex",
    "allowedTopLevel": [
        "README.md",
        "AGENTS.md",
        "index.md",
        "log.md",
        ".open-questions",
        ".project-owner-actions",
        ".rules",
        ".state",
    ],
    "datedFolders": {
        "paths": [],
        "format": "DDMMYYYY-HHMM",
    },
    "readmeRequired": [],
    "frontmatter": {
        "appliesTo": ["**/README.md", "**/AGENTS.md"],
        "required": [
            "title",
            "slug",
            "type",
            "status",
            "owner",
            "created",
            "updated",
        ],
        "enum": {
            "status": ["draft", "active", "deprecated"],
        },
    },
    "naming": {
        "exceptions": [
            "README.md",
            "AGENTS.md",
            "CHANGELOG.md",
            "CONVENTIONS.md",
            ".resolved",
        ],
    },
    "codeToDocMapping": [],
    "log": {
        "path": "log.md",
        "entryPrefix": "## [{date}] {event} | {subject}",
    },
    "index": {
        "path": "index.md",
        "sections": [],
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config_from(project_root: str) -> dict[str, Any] | None:
    """Load memex.config.json from a known project root. Returns merged config."""
    primary = os.path.join(project_root, "memex.config.json")
    fallback = os.path.join(project_root, ".memex", "memex.config.json")
    for path in (primary, fallback):
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    user = json.load(f)
            except Exception:
                return None
            return _deep_merge(DEFAULT_CONFIG, user)
    return None


def load_config_for_file(file_path: str) -> dict[str, Any] | None:
    """Locate the project root by walking up from file_path, then load config."""
    project_root = find_project_root(file_path)
    if not project_root:
        return None
    cfg = load_config_from(project_root)
    if cfg is None:
        return None
    cfg["__project_root"] = project_root
    return cfg
