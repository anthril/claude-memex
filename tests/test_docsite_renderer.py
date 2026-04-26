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
    """Basic title + body extraction. The leading body H1 is promoted to
    `title` and stripped from the rendered body (page template owns the
    chrome H1) — body markdown like the trailing `## Subhead` is preserved."""
    (tmp_path / "page.md").write_text(
        "# Hello\n\nSome text.\n\n## Subhead\n\nMore.\n"
    )
    rendered = renderer.render(
        "# Hello\n\nSome text.\n\n## Subhead\n\nMore.\n", "page", tmp_path
    )
    assert rendered.title == "Hello"
    assert "<h1" not in rendered.html  # leading H1 stripped
    assert "<p>Some text." in rendered.html
    assert "<h2" in rendered.html  # subheadings preserved
    # The leading H1 is consumed before mistune sees it, so it doesn't
    # appear in the captured headings list — only deeper headings remain.
    assert rendered.headings == [(2, "subhead", "Subhead")]


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


def test_renderer_strips_body_h1_even_when_it_differs_from_frontmatter_title():
    """Stripping is unconditional — the page template always renders the
    title as a chrome <h1>, so any body-leading H1 below it would visually
    duplicate. Frontmatter title wins as the page title; body H1 is
    discarded for chrome purposes (its text becomes the URL anchor target
    via the heading-id tracker, but it's not re-rendered as a body <h1>)."""
    src = "---\ntitle: Anthropic\n---\n\n# Anthropic, the company\n\nBody.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert "<h1" not in rendered.html
    assert rendered.title == "Anthropic"  # frontmatter wins


def test_renderer_promotes_body_h1_to_title_when_no_frontmatter():
    """No frontmatter title → the body's first H1 becomes the title and is
    stripped from the body (avoiding the chrome+body duplicate)."""
    src = "# Standalone Page\n\nBody.\n"
    rendered = renderer.render(src, "x", Path("/tmp"))
    assert rendered.title == "Standalone Page"
    assert "<h1" not in rendered.html
    assert "Body." in rendered.html


def test_renderer_resolves_asset_links_when_file_exists(tmp_path: Path):
    """Links to non-markdown assets (.json, .svg, .pdf, .png, etc.) that
    exist alongside the markdown source should resolve to a non-broken URL.
    Previously the renderer only matched .md files, so every link to a JSON
    schema or SVG diagram got marked broken even when the file was right
    there."""
    # Lay out: <wiki>/spec/page.md → ../schemas/event.schema.json
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "event.schema.json").write_text("{}")
    (tmp_path / "spec").mkdir()
    src = "Link to [event schema](../schemas/event.schema.json) here."
    rendered = renderer.render(src, "spec/page", tmp_path)
    assert rendered.broken_links == []
    assert 'href="/schemas/event.schema.json"' in rendered.html


def test_renderer_resolves_folder_links_with_readme(tmp_path: Path):
    """Folder links like `decisions/` should resolve when the folder
    contains README.md (not just index.md). Aurora and most markdown
    repos use README.md as the folder landing page; the resolver was
    only checking index.md and the top-level README."""
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "README.md").write_text("# Decisions")
    src = "See [decisions](decisions/) for the log."
    rendered = renderer.render(src, "index", tmp_path)
    assert rendered.broken_links == []


def test_renderer_resolves_folder_links_to_directories_with_no_readme(
    tmp_path: Path,
):
    """If a folder exists but has no README/index, the link still resolves
    — the live server's `_folder_response` will auto-generate a folder
    index. Marking the link broken would surface a false positive."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "study-1").mkdir()
    (tmp_path / "data" / "study-1" / "README.md").write_text("# Study 1")
    src = "Datasets live in [data](data/)."
    rendered = renderer.render(src, "index", tmp_path)
    assert rendered.broken_links == []


def test_renderer_keeps_marking_truly_missing_assets_broken(tmp_path: Path):
    """Sanity — links to genuinely-missing assets still get flagged."""
    src = "Link to [missing](../schemas/does-not-exist.json)."
    rendered = renderer.render(src, "spec/page", tmp_path)
    assert "../schemas/does-not-exist.json" in rendered.broken_links


def test_wikilink_resolves_against_sibling_when_absolute_misses(tmp_path: Path):
    """`[[criterion-1-local-learning]]` from a page at
    `<wiki>/sec/exp/index.md` should resolve to the sibling
    `<wiki>/sec/exp/criterion-1-local-learning.md`, not be marked broken
    just because there's no top-level page with that slug. Mirrors the
    Obsidian-style behaviour most users expect."""
    (tmp_path / "sec" / "exp").mkdir(parents=True)
    (tmp_path / "sec" / "exp" / "criterion-1-local-learning.md").write_text("# C1")
    src = "See [[criterion-1-local-learning]] for details."
    rendered = renderer.render(src, "sec/exp/index", tmp_path)
    assert rendered.broken_links == []
    assert 'href="/sec/exp/criterion-1-local-learning"' in rendered.html


def test_wikilink_walks_ancestors_for_shared_pages(tmp_path: Path):
    """A wikilink to a page that lives higher in the tree (e.g. a shared
    helper at the wiki root) should still resolve."""
    (tmp_path / "shared-helper.md").write_text("# Shared")
    (tmp_path / "deep" / "nested" / "spot").mkdir(parents=True)
    (tmp_path / "deep" / "nested" / "spot" / "page.md").write_text("body")
    src = "See [[shared-helper]]."
    rendered = renderer.render(src, "deep/nested/spot/page", tmp_path)
    assert rendered.broken_links == []
    assert 'href="/shared-helper"' in rendered.html


def test_wikilink_absolute_match_still_wins(tmp_path: Path):
    """If both an absolute match and a sibling exist, the absolute (root)
    match wins — preserves the existing wiki-style "every slug is unique"
    contract for projects that rely on it."""
    (tmp_path / "concept.md").write_text("# Top")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "concept.md").write_text("# Sub")
    src = "[[concept]]"
    rendered = renderer.render(src, "sub/page", tmp_path)
    assert 'href="/concept"' in rendered.html  # root, not sub/concept
