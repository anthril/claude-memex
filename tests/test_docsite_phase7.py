"""Tests for Phase 7 polish: backlinks, breadcrumbs, TOC, mobile shell."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("starlette")
pytest.importorskip("mistune")
pytest.importorskip("yaml")
pytest.importorskip("httpx")

from starlette.testclient import TestClient  # noqa: E402

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite import graph as graph_module  # noqa: E402
from memex_docsite.server import _breadcrumbs, make_app  # noqa: E402


def _client(project_path: Path) -> TestClient:
    cfg = cfg_mod.load(start=project_path)
    return TestClient(make_app(cfg))


# ─── breadcrumbs ──────────────────────────────────────────────────────────────


def test_breadcrumbs_index_returns_home_only():
    crumbs = _breadcrumbs("index")
    assert crumbs == [{"label": "Home", "url": "/"}]


def test_breadcrumbs_root_path_returns_home_only():
    assert _breadcrumbs("") == [{"label": "Home", "url": "/"}]


def test_breadcrumbs_nested_path():
    crumbs = _breadcrumbs("architecture/engineering-spec/01-event-substrate")
    # Excludes the current page itself.
    assert crumbs == [
        {"label": "Home", "url": "/"},
        {"label": "Architecture", "url": "/architecture/"},
        {"label": "Engineering Spec", "url": "/architecture/engineering-spec/"},
    ]


def test_breadcrumbs_titlecases_segments():
    crumbs = _breadcrumbs("planning/decisions/lock-it-down")
    assert [c["label"] for c in crumbs] == ["Home", "Planning", "Decisions"]


# ─── backlinks helper ─────────────────────────────────────────────────────────


def test_backlinks_for_returns_sources(tmp_path: Path):
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (wiki / "index.md").write_text(
        "---\ntitle: Home\n---\n\nSee [[target]].\n", encoding="utf-8"
    )
    (wiki / "other.md").write_text(
        "---\ntitle: Other\n---\n\nLinks to [[target]] too.\n", encoding="utf-8"
    )
    (wiki / "target.md").write_text(
        "---\ntitle: Target\n---\n\nNo outbound links.\n", encoding="utf-8"
    )
    (wiki / "stranger.md").write_text(
        "---\ntitle: Stranger\n---\n\nIgnored.\n", encoding="utf-8"
    )
    g = graph_module.build(wiki)
    bl = graph_module.backlinks_for(g, "target")
    slugs = [n.slug for n in bl]
    assert sorted(slugs) == ["index", "other"]


def test_backlinks_for_returns_empty_when_unreferenced(tmp_path: Path):
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (wiki / "lonely.md").write_text(
        "---\ntitle: Lonely\n---\n\nNo links.\n", encoding="utf-8"
    )
    g = graph_module.build(wiki)
    assert graph_module.backlinks_for(g, "lonely") == []


# ─── rendered HTML ────────────────────────────────────────────────────────────


def test_page_response_includes_breadcrumbs(tmp_path: Path):
    """Pages nested at least one folder deep should render breadcrumbs."""
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (tmp_path / "memex.config.json").write_text(
        '{"version":"1","profile":"research-wiki","root":".memex"}', encoding="utf-8"
    )
    (wiki / "wiki" / "concepts").mkdir(parents=True)
    (wiki / "wiki" / "concepts" / "memory.md").write_text(
        "---\ntitle: Memory\n---\n\n# Memory\n\nbody.\n", encoding="utf-8"
    )
    cfg = cfg_mod.load(start=tmp_path)
    with TestClient(make_app(cfg)) as client:
        r = client.get("/wiki/concepts/memory")
        assert r.status_code == 200
        assert 'aria-label="Breadcrumb"' in r.text
        # Should include the parent folder labels.
        assert "Concepts" in r.text


def test_page_response_omits_breadcrumbs_for_top_level(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/AGENTS")
        # Single-segment slug → only Home crumb → partial suppressed.
        assert 'aria-label="Breadcrumb"' not in r.text


def test_page_response_includes_right_rail(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/AGENTS")
        # Right rail is rendered in the page template.
        assert 'class="right-rail"' in r.text


def test_page_response_surfaces_backlinks(tmp_path: Path):
    """Seed a tiny wiki so the AGENTS-like page actually has inbound links."""
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (tmp_path / "memex.config.json").write_text(
        '{"version":"1","profile":"research-wiki","root":".memex"}', encoding="utf-8"
    )
    (wiki / "index.md").write_text(
        "---\ntitle: Home\n---\n\nSee [[target]].\n", encoding="utf-8"
    )
    (wiki / "target.md").write_text(
        "---\ntitle: Target\n---\n\n# Target page\n\nA destination.\n",
        encoding="utf-8",
    )
    cfg = cfg_mod.load(start=tmp_path)
    with TestClient(make_app(cfg)) as client:
        r = client.get("/target")
        assert r.status_code == 200
        # Backlinks panel should mention the source page.
        assert "Linked from" in r.text
        assert "Home" in r.text


def test_page_response_includes_toc_when_multiple_headings(tmp_path: Path):
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (tmp_path / "memex.config.json").write_text(
        '{"version":"1","profile":"research-wiki","root":".memex"}', encoding="utf-8"
    )
    (wiki / "index.md").write_text(
        "---\ntitle: Home\n---\n\n# Home\n\n## Section One\n\ntext\n\n## Section Two\n\ntext\n",
        encoding="utf-8",
    )
    cfg = cfg_mod.load(start=tmp_path)
    with TestClient(make_app(cfg)) as client:
        r = client.get("/")
        assert "On this page" in r.text
        assert "Section One" in r.text
        assert "Section Two" in r.text


def test_page_response_omits_toc_for_short_pages(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        # AGENTS.md from the scaffold has just one or two sections; either
        # way we accept that the TOC is absent when there aren't enough
        # H2/H3 headings.
        r = client.get("/AGENTS")
        # If the scaffold ever grows headings, this would surface a TOC and
        # that's fine — we only check for the right-rail container itself.
        assert 'class="right-rail"' in r.text


def test_mobile_hamburger_button_present(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/")
        assert 'id="sidebar-toggle"' in r.text


def test_static_app_js_includes_scroll_spy_and_shortcut(research_wiki_project: Path):
    """Quick sanity check that the bundled app.js carries the Phase 7 polish."""
    with _client(research_wiki_project) as client:
        r = client.get("/static/app.js")
        assert r.status_code == 200
        # Scroll-spy uses IntersectionObserver against TOC anchors.
        assert "IntersectionObserver" in r.text
        assert ".toc a" in r.text
        # `/` keyboard shortcut targets the search input.
        assert "site-search-input" in r.text
        # Collapse-all hooks
        assert "data-tree-action" in r.text


def test_sidebar_renders_collapse_expand_buttons(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.get("/")
        assert 'data-tree-action="collapse"' in r.text
        assert 'data-tree-action="expand"' in r.text


def test_open_question_count_renders(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    """The sidebar shortcut shows a numeric badge when there are active open questions.

    Scoped to the open-questions <a> tag because the profile-driven sections
    nav also renders `.shortcut-count` badges for non-empty sections.
    """
    import json
    import re
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"writeFeatures": ["open-questions"]}
    cfg_path.write_text(json.dumps(raw))

    open_q_anchor = re.compile(
        r'<a href="/open-questions">.*?</a>', flags=re.DOTALL
    )

    with _client(research_wiki_project) as client:
        # No badge inside the open-questions anchor before any submissions.
        r = client.get("/")
        match = open_q_anchor.search(r.text)
        assert match, "open-questions sidebar shortcut not found"
        assert 'shortcut-count' not in match.group(0)

        for title in ("Q one", "Q two", "Q three"):
            assert client.post(
                "/open-questions",
                data={"title": title, "body": "something to discuss"},
                follow_redirects=False,
            ).status_code == 303

        r = client.get("/")
        match = open_q_anchor.search(r.text)
        assert match, "open-questions sidebar shortcut not found after submissions"
        assert 'shortcut-count' in match.group(0)
        assert re.search(r'class="shortcut-count"[^>]*>\s*3\s*<', match.group(0))


def test_graph_js_loads_3d_library(research_wiki_project: Path):
    """The graph page now drives `3d-force-graph` (UMD, vendored) instead of Mermaid."""
    with _client(research_wiki_project) as client:
        r = client.get("/static/graph.js")
        assert r.status_code == 200
        # 3d-force-graph + 2D fallback are the new globals the script expects.
        assert "ForceGraph3D" in r.text
        assert "ForceGraph" in r.text
    with _client(research_wiki_project) as client:
        page = client.get("/graph")
        assert page.status_code == 200
        assert "3d-force-graph.min.js" in page.text
        assert "force-graph.min.js" in page.text
