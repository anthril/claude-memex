"""Current plugin version + lightweight SemVer compare helpers.

The single source of truth is `.claude-plugin/plugin.json`. This module reads
it once at import time so every hook sees the same version.
"""
from __future__ import annotations

import json
import os
import re

_PLUGIN_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".claude-plugin", "plugin.json")
)


def _load_version() -> str:
    try:
        with open(_PLUGIN_JSON, encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


CURRENT_VERSION: str = _load_version()


SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-.]([a-zA-Z0-9.-]+))?$")


def parse_semver(v: str) -> tuple[int, int, int, str] | None:
    """Parse a SemVer-ish string into (major, minor, patch, pre)."""
    if not v:
        return None
    m = SEMVER_RE.match(v.strip())
    if not m:
        return None
    major, minor, patch, pre = m.groups()
    return int(major), int(minor), int(patch), (pre or "")


def is_newer(candidate: str, current: str) -> bool:
    """True if `candidate` > `current` under pragmatic SemVer rules.

    Rules:
    - Parse both; if either fails to parse, return False (conservative)
    - Numeric (major, minor, patch) compared as tuples
    - A release (no pre-release suffix) is newer than any pre-release of the
      same (major, minor, patch) triple — so `1.0.0` > `1.0.0-alpha.1`
    - Pre-release suffixes are compared lexicographically (pragmatic; good
      enough for "is there an update" checks without pulling in a SemVer lib)
    """
    c = parse_semver(candidate)
    curr = parse_semver(current)
    if not c or not curr:
        return False
    c_num, curr_num = c[:3], curr[:3]
    if c_num > curr_num:
        return True
    if c_num < curr_num:
        return False
    # Same core version → compare pre-release
    c_pre, curr_pre = c[3], curr[3]
    if not c_pre and curr_pre:
        return True  # release beats pre-release
    if c_pre and not curr_pre:
        return False
    if c_pre and curr_pre:
        return c_pre > curr_pre
    return False
