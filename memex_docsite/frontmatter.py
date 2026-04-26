"""Richer frontmatter parser for the docsite layer.

Hooks use a flat `key: value` parser (`hooks/scripts/_lib/frontmatter.py`)
because they only need to validate top-level fields. The docsite needs
nested values (e.g., `selector:` blocks on annotations), so we use PyYAML
here. PyYAML is part of the docsite optional-dependency group, so hooks
remain stdlib-only.
"""
from __future__ import annotations

import re

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?", re.DOTALL)


def split(content: str) -> tuple[dict | None, str]:
    """Return (frontmatter_dict_or_None, body)."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None, content
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None, content
    if not isinstance(data, dict):
        return None, content
    body = content[match.end() :]
    return data, body


def serialize(frontmatter: dict, body: str) -> str:
    """Render frontmatter + body back into a single markdown string."""
    yaml_block = yaml.safe_dump(
        frontmatter, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).strip()
    return f"---\n{yaml_block}\n---\n\n{body.lstrip()}"


def validate(
    content: str,
    required: list[str],
    enums: dict[str, list[str]] | None = None,
) -> tuple[bool, str]:
    """Validate frontmatter against required fields and enum constraints.

    Mirrors `hooks/scripts/_lib/frontmatter.py::validate` so the docsite
    rejects exactly the writes the PostToolUse hook would reject. The
    docsite cannot reuse the hook implementation directly because hook
    scripts aren't shipped in the installed Python package — they ride
    the plugin repo. The pair is covered by a parity test in
    `tests/test_docsite_frontmatter_parity.py`.
    """
    fm, _ = split(content)
    if fm is None:
        return False, (
            f"missing YAML frontmatter. Required fields: {', '.join(required)}"
        )

    missing = [k for k in required if not fm.get(k)]
    if missing:
        return False, f"missing required field(s): {', '.join(missing)}"

    if enums:
        for key, allowed in enums.items():
            val = fm.get(key)
            if val is not None and val not in allowed:
                return False, (
                    f"field '{key}' has invalid value '{val}'. "
                    f"Allowed: {', '.join(allowed)}"
                )

    return True, ""
