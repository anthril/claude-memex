"""Parity test — `memex_docsite.config_defaults.DEFAULT_CONFIG` must match
`hooks.scripts._lib.config.DEFAULT_CONFIG` byte-for-byte.

Same pattern as `test_docsite_frontmatter_parity.py`. The two copies exist
because the hook scripts run as standalone Python files that can't import
the optional `memex_docsite` package.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks" / "scripts"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

pytest.importorskip("yaml")  # docsite import side-effects need pyyaml

from _lib import config as hooks_config  # noqa: E402

from memex_docsite import config_defaults as docsite_defaults  # noqa: E402


def test_default_config_matches():
    assert docsite_defaults.DEFAULT_CONFIG == hooks_config.DEFAULT_CONFIG, (
        "DEFAULT_CONFIG drift between memex_docsite.config_defaults and "
        "hooks/scripts/_lib/config.py — keep them in sync."
    )


def test_deep_merge_matches_behaviour():
    """Both deep-merge implementations must produce identical output."""
    base = {"a": 1, "b": {"c": 2, "d": 3}, "e": [1, 2]}
    override = {"b": {"d": 99, "x": "new"}, "e": [9]}
    docsite_out = docsite_defaults.deep_merge(base, override)
    hooks_out = hooks_config._deep_merge(base, override)
    assert docsite_out == hooks_out
    # Sanity: nested dict was merged, list was replaced (not concatenated).
    assert docsite_out["b"] == {"c": 2, "d": 99, "x": "new"}
    assert docsite_out["e"] == [9]
