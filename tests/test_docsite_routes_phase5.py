"""Tests for the comments HTTP routes (Phase 5)."""
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
from memex_docsite.server import make_app  # noqa: E402


def _enable_comments(project: Path, *, auth: str = "none") -> Path:
    cfg_path = project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {
        "enabled": True,
        "auth": auth,
        "writeFeatures": ["comments"],
    }
    cfg_path.write_text(json.dumps(raw))
    return project


def _client(project_path: Path) -> TestClient:
    cfg = cfg_mod.load(start=project_path)
    return TestClient(make_app(cfg))


def test_create_returns_201(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/api/comments/architecture/concept",
            json={"body": "Hello"},
        )
        assert r.status_code == 201
        rec = r.json()
        assert rec["body"] == "Hello"
        assert rec["status"] == "active"
        assert rec["author"] == "anonymous"


def test_list_returns_created_records(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        client.post("/api/comments/page", json={"body": "first"})
        client.post("/api/comments/page", json={"body": "second"})
        r = client.get("/api/comments/page")
        bodies = [rec["body"] for rec in r.json()]
        assert bodies == ["first", "second"]


def test_create_404_when_writes_disabled(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.post("/api/comments/page", json={"body": "x"})
        assert r.status_code == 404


def test_get_works_when_writes_disabled(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        client.post("/api/comments/page", json={"body": "x"})

    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"]["writeFeatures"] = []
    cfg_path.write_text(json.dumps(raw))

    with _client(research_wiki_project) as client:
        r = client.get("/api/comments/page")
        assert r.status_code == 200
        assert len(r.json()) == 1


def test_invalid_body_returns_400(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post("/api/comments/page", json={"body": "  "})
        assert r.status_code == 400
        assert "body is required" in r.json()["error"]


def test_replies_route(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post("/api/comments/page", json={"body": "parent"})
        parent_id = r.json()["id"]
        r = client.post(
            "/api/comments/page",
            json={"body": "reply", "replies_to": parent_id},
        )
        assert r.status_code == 201
        assert r.json()["replies_to"] == parent_id


def test_replies_to_unknown_parent_returns_404(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/api/comments/page",
            json={"body": "reply", "replies_to": "ghost"},
        )
        assert r.status_code == 404


def test_update_then_delete(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post("/api/comments/page", json={"body": "orig"})
        cid = r.json()["id"]
        r = client.patch(f"/api/comments/page/{cid}", json={"body": "revised"})
        assert r.status_code == 200
        assert r.json()["body"] == "revised"
        r = client.delete(f"/api/comments/page/{cid}")
        assert r.status_code == 200
        items = client.get("/api/comments/page").json()
        deleted = next(c for c in items if c["id"] == cid)
        assert deleted["status"] == "deleted"


def test_token_mode_blocks_unauthenticated(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_comments(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = client.post("/api/comments/page", json={"body": "x"})
        assert r.status_code == 401


def test_global_comments_overview(research_wiki_project: Path):
    _enable_comments(research_wiki_project)
    with _client(research_wiki_project) as client:
        client.post("/api/comments/page-a", json={"body": "alpha"})
        client.post("/api/comments/page-b", json={"body": "beta"})
        r = client.get("/comments")
        assert r.status_code == 200
        assert "Recent comments" in r.text
        assert "alpha" in r.text
        assert "beta" in r.text
        assert "page-a" in r.text and "page-b" in r.text


def test_token_mode_allows_with_bearer(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_comments(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = client.post(
            "/api/comments/page",
            json={"body": "ok"},
            headers={"Authorization": "Bearer s3cret"},
        )
        assert r.status_code == 201
