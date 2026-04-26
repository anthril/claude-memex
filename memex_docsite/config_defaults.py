"""Shared default config + deep-merge for `memex.config.json`.

Mirror of `hooks/scripts/_lib/config.py`'s `DEFAULT_CONFIG` and `_deep_merge`.
Two copies exist by design — the hook scripts ship as standalone Python files
that can't depend on the importable `memex_docsite` package (which itself
has third-party deps gated behind the `[docsite]` extra). Parity is asserted
by `tests/test_docsite_config_defaults_parity.py`, same pattern as
`frontmatter.py` ↔ `_lib/frontmatter.py`.

Stdlib-only on purpose. Do not import anything outside `typing`.
"""
from __future__ import annotations

from typing import Any

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


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursive merge — override wins for non-dict values; dicts merge."""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def apply_defaults(user_config: dict[str, Any]) -> dict[str, Any]:
    """Merge a user-supplied config on top of the defaults."""
    return deep_merge(DEFAULT_CONFIG, user_config)
