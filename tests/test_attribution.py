"""Karpathy / llm-wiki.md attribution is present everywhere it must be.

Breakage here means we've accidentally removed credit — serious enough to
fail CI.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

REQUIRED_ATTRIBUTIONS = [
    (REPO / "README.md", "llm-wiki.md", "README must link to the gist"),
    (REPO / "README.md", "Karpathy", "README must name Karpathy"),
    (REPO / "CREDITS.md", "Karpathy", "CREDITS must name Karpathy"),
    (REPO / "CREDITS.md", "442a6bf555914893e9891c11519de94f", "CREDITS must link to the actual gist URL"),
    (REPO / "docs" / "concepts.md", "Karpathy", "concepts.md must credit Karpathy"),
    (REPO / "templates" / "profiles" / "engineering-ops" / ".memex" / "AGENTS.md", "Karpathy",
     "engineering-ops AGENTS.md must credit Karpathy"),
    (REPO / "templates" / "profiles" / "research-wiki" / ".memex" / "AGENTS.md", "Karpathy",
     "research-wiki AGENTS.md must credit Karpathy"),
    (REPO / "templates" / "profiles" / "research-wiki" / ".memex" / "README.md", "Karpathy",
     "research-wiki README must credit Karpathy (most literal adaptation)"),
    (REPO / "templates" / "profiles" / "book-companion" / ".memex" / "AGENTS.md", "Karpathy",
     "book-companion AGENTS.md must credit Karpathy"),
    (REPO / "templates" / "profiles" / "personal-journal" / ".memex" / "AGENTS.md", "Karpathy",
     "personal-journal AGENTS.md must credit Karpathy"),
]


@pytest.mark.parametrize("path,needle,reason", REQUIRED_ATTRIBUTIONS)
def test_attribution_present(path, needle, reason):
    assert path.exists(), f"{path} does not exist"
    content = path.read_text(encoding="utf-8")
    assert needle in content, reason


def test_llm_wiki_not_included_verbatim():
    """The gist is linked, not redistributed.

    Historically we shipped `llm-wiki.md` at the repo root verbatim. That was
    changed to a link-only attribution so the repo doesn't redistribute the
    gist content. If this test fails, someone has re-added a local copy —
    make sure that's what you want, and update CREDITS.md if so.
    """
    assert not (REPO / "llm-wiki.md").exists(), \
        "llm-wiki.md should NOT be at the repo root — link to the gist instead"


def test_credits_has_karpathy_github_links():
    content = (REPO / "CREDITS.md").read_text(encoding="utf-8")
    assert "gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" in content
    assert "github.com/karpathy" in content


def test_license_is_mit():
    content = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "MIT" in content
