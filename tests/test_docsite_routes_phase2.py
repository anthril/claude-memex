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
