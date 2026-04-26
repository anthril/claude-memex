"""Tests for the markdown→HTML pipeline (Phase 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

# Skip the whole module if docsite extras aren't installed.
pytest.importorskip("mistune")
pytest.importorskip("yaml")

from memex_docsite import frontmatter, renderer, resolver  # noqa: E402


def test_frontmatter_split_and_serialize_round_trip():
    src = """---
title: Demo
type: concept
selector:
  type: TextQuoteSelector
  exact: hello world
---

Body text here.
"""
    fm, body = frontmatter.split(src)
    assert fm == {
        "title": "Demo",
        "type": "concept",
        "selector": {"type": "TextQuoteSelector", "exact": "hello world"},
    }
    assert body.strip() == "Body text here."

    rebuilt = frontmatter.serialize(fm, body)
    fm2, body2 = frontmatter.split(rebuilt)
    assert fm2 == fm
    assert body2.strip() == body.strip()


def test_frontmatter_handles_missing_block():
    src = "no frontmatter here\n"
    fm, body = frontmatter.split(src)
    assert fm is None
    assert body == src


def test_resolver_path_to_slug(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    file = tmp_path / "sub" / "page.md"
    file.write_text("# x")
    assert resolver.path_to_slug(file, tmp_path) == "sub/page"
    assert resolver.path_to_slug(tmp_path / "index.md", tmp_path) == "index"


def test_resolver_slug_to_url():
    assert resolver.slug_to_url("index") == "/"
    assert resolver.slug_to_url("sub/page") == "/sub/page"
    assert resolver.slug_to_url("sub/index") == "/sub/"
    assert resolver.slug_to_url("") == "/"


def test_resolver_slug_to_path_blocks_traversal(tmp_path: Path):
    (tmp_path / "outside.md").write_text("# x")
    inner = tmp_path / "wiki"
    inner.mkdir()
    # Should refuse to escape the wiki root.
    assert resolver.slug_to_path("../outside", inner) is None


def test_resolver_relative_link_resolution(tmp_path: Path):
    (tmp_path / "a.md").write_text("# a")
    (tmp_path / "b" / "c.md").parent.mkdir()
    (tmp_path / "b" / "c.md").write_text("# c")

    # From `b/c`, `../a` → `a`
    assert resolver.resolve_relative("../a", "b/c", tmp_path) == "a"
    # From `b/c`, `c.md` → `b/c`
    assert resolver.resolve_relative("c.md", "b/c", tmp_path) == "b/c"
    # External / absolute / anchor links should not be resolved.
    assert resolver.resolve_relative("https://x.com", "b/c", tmp_path) is None
    assert resolver.resolve_relative("#heading", "b/c", tmp_path) is None
    # Broken links return None.
    assert resolver.resolve_relative("nope", "b/c", tmp_path) is None


def test_renderer_basic_round_trip(tmp_path: Path):
    (tmp_path / "page.md").write_text("# Hello\n\nSome text.\n")
    rendered = renderer.render("# Hello\n\nSome text.\n", "page", tmp_path)
    assert rendered.title == "Hello"
    assert "<h1" in rendered.html and "Hello" in rendered.html
    assert "<p>Some text." in rendered.html
    assert rendered.headings == [(1, "hello", "Hello")]


def test_renderer_wikilink_and_relative_link(tmp_path: Path):
    (tmp_path / "target.md").write_text("# Target")
    md = "Link to [[target|the target]] and [rel](target)."
    rendered = renderer.render(md, "index", tmp_path)
    assert 'href="/target"' in rendered.html
    assert "the target" in rendered.html
    assert rendered.broken_links == []


def test_renderer_flags_broken_links(tmp_path: Path):
    md = "Bad [[ghost]] and [also-bad](missing)."
    rendered = renderer.render(md, "index", tmp_path)
    assert "ghost" in rendered.broken_links
    assert "missing" in rendered.broken_links
    assert "memex-broken" in rendered.html


def test_renderer_uses_frontmatter_title():
    src = "---\ntitle: Custom Title\n---\n\n# Page Heading\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert rendered.title == "Custom Title"
    assert rendered.frontmatter["title"] == "Custom Title"


def test_renderer_strips_body_h1_matching_frontmatter_title():
    """When the frontmatter `title` and the body's first H1 are the same,
    the body H1 is stripped — the page template already renders the title
    as `<h1>{{ page.title }}</h1>` and we don't want the duplicate.
    """
    src = "---\ntitle: AURORA\n---\n\n# AURORA\n\nBody copy here.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    # Body H1 removed; the only "AURORA" reference is the frontmatter title.
    assert "<h1" not in rendered.html
    assert "Body copy here." in rendered.html
    assert rendered.title == "AURORA"


def test_renderer_keeps_body_h1_when_it_differs_from_title():
    """If the body's first H1 differs from the frontmatter title (e.g. an
    abbreviation expansion or a different framing), keep both — the
    duplicate-title strip is opt-in to exact matches only."""
    src = "---\ntitle: Anthropic\n---\n\n# Anthropic, the company\n\nBody.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert "<h1" in rendered.html
    assert "Anthropic, the company" in rendered.html


def test_renderer_keeps_body_h1_when_no_frontmatter_title():
    """No frontmatter title → no duplicate to strip; the body H1 stays."""
    src = "# Standalone Page\n\nBody.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert "<h1" in rendered.html
    assert "Standalone Page" in rendered.html


def test_renderer_strip_is_case_insensitive():
    """Match is case-insensitive — `# aurora` strips against `title: AURORA`."""
    src = "---\ntitle: AURORA\n---\n\n# aurora\n\nBody.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert "<h1" not in rendered.html
