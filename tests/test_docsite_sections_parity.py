"""Parity test — `memex_docsite.sections.suggest_section` must behave the
same as `hooks/scripts/_lib/index_parse.suggest_section` for every input
combination the hook bus might throw at it.

Same-pattern parity test as for frontmatter / config_defaults.
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

from _lib import index_parse as hooks_index_parse  # noqa: E402

from memex_docsite import sections as docsite_sections  # noqa: E402

CASES = [
    # (sections, rel_path, page_type, expected)
    # page_type='entity' alone doesn't match "Entities" (the heuristic only
    # singularises "X" → "Xs"/"Xes", not depluralises "Xes" → "X"). The
    # folder segment "entities" does match.
    ({"Entities": set(), "Concepts": set()}, "entities/foo.md", "entity", "Entities"),
    ({"Entities": set(), "Concepts": set()}, "concepts/foo.md", None, "Concepts"),
    ({"Entities": set()}, "raw/2024-01/foo.md", "research", None),
    ({}, "wiki/foo.md", "entity", None),
    # Hyphenated types aren't reachable via the heuristic — the schema's
    # array-of-objects form is the supported workaround.
    ({"Open Questions": set()}, ".open-questions/x.md", "open-question", None),
    ({"Topics": set()}, "topics/foo.md", "topic", "Topics"),
    # First-segment match wins.
    ({"Hypotheses": set()}, "hypotheses/h-1.md", "hypothesis", "Hypotheses"),
    # Empty page_type, irrelevant first segment → None.
    ({"Entities": set()}, "raw/foo.md", None, None),
    # Multiple candidates, page_type wins over first_segment.
    ({"Entities": set(), "Topics": set()}, "topics/foo.md", "topic", "Topics"),
]


@pytest.mark.parametrize("sections,rel_path,page_type,expected", CASES)
def test_suggest_section_parity(sections, rel_path, page_type, expected):
    docsite_out = docsite_sections.suggest_section(sections, rel_path, page_type)
    hooks_out = hooks_index_parse.suggest_section(sections, rel_path, page_type)
    assert docsite_out == hooks_out, (
        f"drift between docsite and hooks suggest_section: "
        f"sections={sections} rel_path={rel_path} page_type={page_type} → "
        f"docsite={docsite_out!r}, hooks={hooks_out!r}"
    )
    # Sanity: still in the section list when not None.
    if docsite_out is not None:
        assert docsite_out in sections
