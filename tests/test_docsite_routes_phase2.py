"""Tests for the search + graph HTTP routes added in Phase 2."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("starlette")
pytest.importorskip("mistune")
pytest.importorskip("yaml")
pytest.importorskip("httpx")

from starlette.testclient import TestClient  # noqa: E402

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite.server import make_app  # noqa: E402


def _client(project_path: Path) -> TestClient:
    cfg = cfg_mod.load(start=project_path)
    return TestClient(make_app(cfg))


def test_search_empty_query_renders(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/search")
        assert r.status_code == 200
        assert "Search" in r.text


def test_search_with_query(research_wiki_project: Path):
    # Drop a known phrase into the scaffolded wiki so the test is deterministic.
    (research_wiki_project / ".memex" / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
    page = research_wiki_project / ".memex" / "wiki" / "concepts" / "memory-binding.md"
    page.write_text(
        "---\ntitle: Memory binding\ntype: concept\n---\n\n"
        "The hippocampus binds episodes for later replay and consolidation.\n"
    )
    with _client(research_wiki_project) as client:
        r = client.get("/search?q=hippocampus")
        assert r.status_code == 200
        assert "Memory binding" in r.text
        assert "hippocampus" in r.text.lower()


def test_search_no_match(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/search?q=xyzzyabcdef")
        assert r.status_code == 200
        assert "No matches" in r.text


def test_graph_html(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/graph")
        assert r.status_code == 200
        assert "Link graph" in r.text
        assert "/api/graph" in r.text or "graph.js" in r.text


def test_graph_json(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/api/graph")
        assert r.status_code == 200
        payload = r.json()
        assert "nodes" in payload and "edges" in payload and "summary" in payload
        assert payload["summary"]["node_count"] == len(payload["nodes"])


def test_sections_overview_renders(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/sections")
        assert r.status_code == 200
        # research-wiki defines an Entities section.
        assert "Sections" in r.text
        assert "Entities" in r.text


def test_section_detail_renders(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/sections/entities")
        assert r.status_code == 200
        # The empty-state copy includes the type code; check we got the section page.
        assert "Entities" in r.text


def test_section_detail_404_for_unknown_slug(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/sections/does-not-exist")
        assert r.status_code == 404


def test_sidebar_nav_suppresses_shortcut_duplicates(research_wiki_project: Path):
    """Sections whose slug duplicates a hardcoded sidebar shortcut
    (Open Questions, Rules, Comments, Link graph) should not appear a
    second time in the sections nav."""
    import json
    import re
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    # Stack the deck — declare both Open Questions AND Rule(s) as sections,
    # then verify they're filtered from the sidebar nav (still rendered as
    # /sections/<slug>/ landing pages, just not in the chrome).
    raw["index"]["sections"] = ["Entities", "Concepts", "Open Questions", "Rules"]
    cfg_path.write_text(json.dumps(raw))

    with _client(research_wiki_project) as client:
        r = client.get("/")
        assert r.status_code == 200
        block = re.search(
            r'<nav class="sidebar-sections".*?</nav>', r.text, re.DOTALL
        )
        assert block, "sidebar-sections nav not rendered"
        nav = block.group(0)
        # Still includes the proper content sections.
        assert "Entities" in nav
        assert "Concepts" in nav
        # Suppresses the duplicates.
        assert "Open Questions" not in nav
        assert "Rules" not in nav
        # The auto-appended `rule` synthetic section is also suppressed
        # (it would have been a singular "Rule" otherwise).
        assert "/sections/rule" not in nav
        assert "/sections/rules" not in nav
        assert "/sections/open-questions" not in nav


def test_page_route_serves_asset_files(research_wiki_project: Path):
    """The page route should serve non-markdown asset files (JSON schemas,
    SVG diagrams, PDFs, etc.) when the literal path matches a file under
    the wiki root. Otherwise links to those files get 404 even when the
    file exists right where the markdown referenced it."""
    asset_dir = research_wiki_project / ".memex" / "schemas"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "event.schema.json").write_text('{"type":"object"}')
    with _client(research_wiki_project) as client:
        r = client.get("/schemas/event.schema.json")
        assert r.status_code == 200
        assert r.json() == {"type": "object"}


def test_page_route_404s_for_missing_asset(research_wiki_project: Path):
    """Sanity — a non-existent asset path still 404s."""
    with _client(research_wiki_project) as client:
        r = client.get("/schemas/does-not-exist.json")
        assert r.status_code == 404


def test_section_detail_renders_collapsible_folder_tree(
    research_wiki_project: Path,
):
    """`/sections/<slug>` should group its pages by folder structure into a
    collapsible `<details>` tree, not render a flat list."""
    # Add a few real pages under wiki/entities so the Entities section
    # has multi-folder content to group.
    import json as _json
    cfg_path = research_wiki_project / "memex.config.json"
    raw = _json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": ".", "showHidden": True}
    cfg_path.write_text(_json.dumps(raw))
    base = research_wiki_project / ".memex" / "wiki" / "entities"
    base.mkdir(parents=True, exist_ok=True)
    for name in ("alpha", "beta"):
        d = base / name
        d.mkdir(exist_ok=True)
        (d / "README.md").write_text(
            f"---\ntitle: {name.title()}\nslug: {name}\ntype: entity\n"
            f"status: active\nowner: x\ncreated: 2026-04-27\n"
            f"updated: 2026-04-27\n---\n\nContent.\n"
        )
    with _client(research_wiki_project) as client:
        r = client.get("/sections/entities")
        assert r.status_code == 200
        # Tree markup is present (not the old flat folder-listing).
        assert 'class="section-tree"' in r.text
        assert 'class="section-tree-folder"' in r.text
        # `<details>` is open by default for first-load discoverability.
        assert "<details" in r.text
        # The folder summaries have count badges.
        assert "section-tree-count" in r.text


def test_folder_index_pages_resolve_relative_links_to_siblings(
    research_wiki_project: Path,
):
    """Regression — when a URL like `/foo/bar/` is served from
    `<wiki>/foo/bar/index.md`, relative links in that file
    (`[Sib](sibling)`) must resolve to `<wiki>/foo/bar/sibling.md`, not
    one level higher. The page route now passes the canonical file slug
    to the renderer (e.g. `foo/bar/index`) so `source_dir` lands inside
    the folder, not at its parent."""
    folder = research_wiki_project / ".memex" / "section-x"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.md").write_text(
        "# Section X\n\nSee [criterion 1](criterion-one) for details.\n"
    )
    (folder / "criterion-one.md").write_text("# Criterion 1\n\nbody\n")
    with _client(research_wiki_project) as client:
        r = client.get("/section-x/")
        assert r.status_code == 200
        assert "broken-links" not in r.text
        # The link should resolve to the sibling under the same folder.
        assert 'href="/section-x/criterion-one"' in r.text
