"""Verify the docsite's frontmatter validator agrees with the hook's.

The docsite ships its own `frontmatter.validate(...)` because the hook
scripts (`hooks/scripts/_lib/frontmatter.py`) aren't shipped in the
installed Python wheel — they ride the plugin repo. This test exercises
both implementations against the same inputs so they don't drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_LIB = REPO_ROOT / "hooks" / "scripts"
if str(HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(HOOKS_LIB))

from _lib import frontmatter as hook_frontmatter  # noqa: E402

from memex_docsite import frontmatter as docsite_frontmatter  # noqa: E402

REQUIRED = ["title", "slug", "type", "status"]
ENUMS = {
    "type": ["concept", "rule", "annotation", "open-question"],
    "status": ["draft", "active", "deprecated"],
}


CASES = [
    # (description, content, expected_ok)
    (
        "valid",
        "---\ntitle: A\nslug: a\ntype: concept\nstatus: active\n---\n\nbody\n",
        True,
    ),
    (
        "missing required",
        "---\ntitle: A\nslug: a\ntype: concept\n---\n\nbody\n",
        False,
    ),
    (
        "invalid enum",
        "---\ntitle: A\nslug: a\ntype: bogus\nstatus: active\n---\n\nbody\n",
        False,
    ),
    (
        "no frontmatter",
        "no frontmatter at all\n",
        False,
    ),
    (
        "empty value treated as missing",
        "---\ntitle:\nslug: a\ntype: concept\nstatus: active\n---\n\nbody\n",
        False,
    ),
]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_validators_agree_on_outcome(case):
    _, content, expected = case
    hook_ok, _hook_msg = hook_frontmatter.validate(content, REQUIRED, ENUMS)
    doc_ok, _doc_msg = docsite_frontmatter.validate(content, REQUIRED, ENUMS)
    assert hook_ok == expected, f"hook validator disagreed on {_!r}"
    assert doc_ok == expected, f"docsite validator disagreed on {_!r}"
    assert hook_ok == doc_ok, "hook and docsite validators disagree"


def test_docsite_handles_nested_frontmatter():
    """The docsite parses YAML; the hook only handles flat key:value pairs.

    For *flat* frontmatter both must agree (covered above). For nested
    frontmatter (e.g. annotation selectors) the docsite must still
    succeed — this is the docsite-specific superset.
    """
    content = (
        "---\n"
        "title: Annotation\n"
        "slug: a\n"
        "type: annotation\n"
        "status: active\n"
        "selector:\n"
        "  type: TextQuoteSelector\n"
        "  exact: hello world\n"
        "---\n\nbody\n"
    )
    ok, _ = docsite_frontmatter.validate(content, REQUIRED, ENUMS)
    assert ok is True
