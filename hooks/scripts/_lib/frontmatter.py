"""YAML frontmatter parse + required-field validation.

No third-party deps — a minimal parser that handles `key: value` pairs inside
`---`-delimited blocks. Sufficient for the flat frontmatter Memex requires.
"""
from __future__ import annotations

import re

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def parse(content: str) -> dict[str, str] | None:
    """Return the parsed frontmatter dict, or None if none present."""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None
    body = m.group(1)
    out: dict[str, str] = {}
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        # strip matching quotes if present
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key] = val
    return out


def validate(
    content: str,
    required: list[str],
    enums: dict[str, list[str]] | None = None,
) -> tuple[bool, str]:
    """Check frontmatter has all required fields and enum values are valid.

    Returns (ok, message). `message` is empty on success.
    """
    parsed = parse(content)
    if parsed is None:
        return False, (
            f"missing YAML frontmatter. Required fields: {', '.join(required)}"
        )

    missing = [k for k in required if not parsed.get(k)]
    if missing:
        return False, f"missing required field(s): {', '.join(missing)}"

    if enums:
        for key, allowed in enums.items():
            val = parsed.get(key)
            if val is not None and val not in allowed:
                return False, (
                    f"field '{key}' has invalid value '{val}'. "
                    f"Allowed: {', '.join(allowed)}"
                )

    return True, ""
