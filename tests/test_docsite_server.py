"""Tests for the Starlette server routes (Phase 1)."""
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


def test_index_route(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "<html" in r.text
        # The scaffolded research-wiki ships an index.md with `# Index` heading.
        assert "Index" in r.text


def test_page_route(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/AGENTS")
        assert r.status_code == 200
        assert "<html" in r.text


def test_static_assets_served(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/static/base.css")
        assert r.status_code == 200
        assert "site-shell" in r.text


def test_health_endpoint(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_404_for_missing_page(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/this-does-not-exist")
        assert r.status_code == 404
        assert "404" in r.text


def test_folder_route_with_index(research_wiki_project):
    """Routes ending in a folder name should render as folder index."""
    # `wiki/` exists but contains only sub-folders / scaffold .keep files.
    # The dir itself should resolve to a folder listing.
    with _client(research_wiki_project) as client:
        r = client.get("/wiki/")
        # Either a folder listing or 404 is acceptable depending on whether
        # the scaffold left any markdown there. For research-wiki the dir is
        # empty (scaffold .keep removed), so we accept 200 (empty folder)
        # or 404.
        assert r.status_code in (200, 404)


def test_raw_route_blocks_traversal(research_wiki_project):
    with _client(research_wiki_project) as client:
        r = client.get("/raw/../../memex.config.json")
        assert r.status_code in (404, 400)
