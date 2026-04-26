"""Tests for the search backend (Phase 2)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import search  # noqa: E402


def _seed_wiki(root: Path) -> None:
    (root / ".memex").mkdir(exist_ok=True)
    wiki = root / ".memex"
    (wiki / "alpha.md").write_text(
        "---\ntitle: Alpha page\n---\n\n"
        "Hippocampus and consolidation help memory binding.\n",
        encoding="utf-8",
    )
    (wiki / "beta.md").write_text(
        "---\ntitle: Beta page\n---\n\n"
        "Hippocampus comes up here too. Again - hippocampus appears.\n",
        encoding="utf-8",
    )
    (wiki / "gamma.md").write_text(
        "---\ntitle: Gamma page\n---\n\n"
        "Nothing related - sparse coding only.\n",
        encoding="utf-8",
    )


def test_search_returns_ranked_results(tmp_path: Path):
    _seed_wiki(tmp_path)
    results = search.search("hippocampus consolidation", tmp_path / ".memex", top_n=10)
    slugs = [r.slug for r in results]
    assert "beta" in slugs[:2]  # Beta has the most occurrences (3)
    assert "alpha" in slugs  # Alpha has 1 occurrence + consolidation match
    assert "gamma" not in slugs


def test_search_empty_query(tmp_path: Path):
    _seed_wiki(tmp_path)
    assert search.search("", tmp_path / ".memex") == []
    assert search.search("   ", tmp_path / ".memex") == []


def test_search_no_matches(tmp_path: Path):
    _seed_wiki(tmp_path)
    assert search.search("xyzzy", tmp_path / ".memex") == []


def test_search_skips_state_dir(tmp_path: Path):
    _seed_wiki(tmp_path)
    state = tmp_path / ".memex" / ".state"
    state.mkdir()
    (state / "secret.md").write_text("hippocampus all over the place", encoding="utf-8")
    results = search.search("hippocampus", tmp_path / ".memex")
    assert all(r.slug != ".state/secret" for r in results)


def test_snippet_contains_query_term(tmp_path: Path):
    _seed_wiki(tmp_path)
    results = search.search("hippocampus", tmp_path / ".memex", top_n=5)
    assert results
    assert any("hippocampus" in r.snippet.lower() for r in results)


def test_search_respects_show_hidden(tmp_path: Path):
    _seed_wiki(tmp_path)
    hidden = tmp_path / ".memex" / ".rules"
    hidden.mkdir()
    (hidden / "secret.md").write_text("hippocampus inside hidden folder", encoding="utf-8")

    visible = search.search("hippocampus", tmp_path / ".memex", show_hidden=True)
    assert any(r.slug == ".rules/secret" for r in visible)

    hidden_only = search.search("hippocampus", tmp_path / ".memex", show_hidden=False)
    assert all(r.slug != ".rules/secret" for r in hidden_only)
