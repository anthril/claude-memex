"""Verify ignorePatterns reaches sitetree, graph, search, and the GET path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("starlette")
pytest.importorskip("mistune")
pytest.importorskip("yaml")
pytest.importorskip("httpx")

from starlette.testclient import TestClient  # noqa: E402

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite import graph as graph_module  # noqa: E402
from memex_docsite import search as search_module  # noqa: E402
from memex_docsite import sitetree  # noqa: E402
from memex_docsite.server import make_app  # noqa: E402


def _seed(project: Path) -> Path:
    """Lay out a project with one wiki page and one ignored page."""
    wiki = project / ".memex"
    wiki.mkdir(exist_ok=True)
    (wiki / "index.md").write_text(
        "---\ntitle: Home\n---\n\nA wiki home.\n", encoding="utf-8"
    )
    junk = wiki / "node_modules"
    junk.mkdir()
    (junk / "vendored.md").write_text(
        "# Vendored\n\nShould not appear.\n", encoding="utf-8"
    )
    (project / "memex.config.json").write_text(
        json.dumps(
            {
                "version": "1",
                "profile": "research-wiki",
                "root": ".memex",
                "docsite": {"ignorePatterns": ["node_modules/**"]},
            }
        ),
        encoding="utf-8",
    )
    return project


def test_sitetree_skips_ignored_paths(tmp_path: Path):
    _seed(tmp_path)
    cfg = cfg_mod.load(start=tmp_path)
    tree = sitetree.build(cfg.wiki_root, show_hidden=cfg.show_hidden, is_ignored=cfg.is_ignored)
    # Walk the tree and confirm node_modules/vendored doesn't surface.
    seen: list[str] = []
    def walk(n):
        if n.slug:
            seen.append(n.slug)
        for c in n.children:
            walk(c)
    walk(tree)
    assert "node_modules/vendored" not in seen
    assert "index" in seen


def test_graph_skips_ignored_paths(tmp_path: Path):
    _seed(tmp_path)
    cfg = cfg_mod.load(start=tmp_path)
    g = graph_module.build(cfg.wiki_root, show_hidden=cfg.show_hidden, is_ignored=cfg.is_ignored)
    slugs = {n.slug for n in g.nodes}
    assert "node_modules/vendored" not in slugs


def test_search_skips_ignored_paths(tmp_path: Path):
    _seed(tmp_path)
    cfg = cfg_mod.load(start=tmp_path)
    # Inject a unique term so we know the file would have matched.
    junk = cfg.wiki_root / "node_modules" / "vendored.md"
    junk.write_text("# Vendored\n\nzzqxv unique-token-here\n", encoding="utf-8")
    results = search_module.search(
        "zzqxv", cfg.wiki_root, show_hidden=cfg.show_hidden, is_ignored=cfg.is_ignored
    )
    assert all("node_modules" not in r.slug for r in results)


def test_get_route_returns_404_for_ignored_path(tmp_path: Path):
    _seed(tmp_path)
    cfg = cfg_mod.load(start=tmp_path)
    with TestClient(make_app(cfg)) as client:
        r = client.get("/node_modules/vendored")
        assert r.status_code == 404
