"""Tests for the annotation HTTP routes (Phase 4)."""
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

_SELECTOR = {
    "type": "TextQuoteSelector",
    "exact": "the hippocampus binds episodes",
    "prefix": "consolidation. ",
    "suffix": " for replay",
}


def _enable_annotations(project: Path, *, auth: str = "none") -> Path:
    cfg_path = project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {
        "enabled": True,
        "auth": auth,
        "writeFeatures": ["annotations"],
    }
    cfg_path.write_text(json.dumps(raw))
    return project


def _client(project_path: Path) -> TestClient:
    cfg = cfg_mod.load(start=project_path)
    return TestClient(make_app(cfg))


def _post_annotation(client, page_slug, **overrides):
    payload = {"body": "Sample note", "selector": _SELECTOR, **overrides}
    return client.post(f"/api/annotations/{page_slug}", json=payload)


# ─── basic CRUD ───────────────────────────────────────────────────────────────


def test_create_returns_201(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "architecture/concept")
        assert r.status_code == 201
        data = r.json()
        assert data["selector"]["exact"] == _SELECTOR["exact"]
        assert data["author"] == "anonymous"
        assert data["status"] == "active"


def test_list_returns_created_items(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        for body in ("first", "second"):
            r = _post_annotation(client, "architecture/concept", body=body)
            assert r.status_code == 201
        r = client.get("/api/annotations/architecture/concept")
        assert r.status_code == 200
        bodies = sorted(a["body"] for a in r.json())
        assert bodies == ["first", "second"]


def test_create_404_when_writes_disabled(research_wiki_project: Path):
    # Default config has empty writeFeatures.
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "architecture/concept")
        assert r.status_code == 404


def test_list_works_without_writes(research_wiki_project: Path):
    """GET should always succeed; only writes are gated."""
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        _post_annotation(client, "page-a")

    # Disable writes and confirm the GET still returns the existing items.
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"]["writeFeatures"] = []
    cfg_path.write_text(json.dumps(raw))

    with _client(research_wiki_project) as client:
        r = client.get("/api/annotations/page-a")
        assert r.status_code == 200
        assert len(r.json()) == 1


def test_create_invalid_selector_returns_400(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/api/annotations/page",
            json={"body": "x", "selector": {"type": "TextQuoteSelector", "exact": ""}},
        )
        assert r.status_code == 400
        assert "selector.exact" in r.json()["error"]


def test_update_author_only(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "page", body="orig")
        ann_id = r.json()["id"]

        # In auth=none mode, the form's `author` field becomes the identity.
        # Same identity (default "anonymous") can update.
        r = client.patch(
            f"/api/annotations/page/{ann_id}",
            json={"body": "updated"},
        )
        assert r.status_code == 200
        assert r.json()["body"] == "updated"


def test_delete_marks_status(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "page")
        ann_id = r.json()["id"]
        r = client.delete(f"/api/annotations/page/{ann_id}")
        assert r.status_code == 200
        # GET should still surface the tombstone.
        r = client.get("/api/annotations/page")
        items = r.json()
        assert any(a["id"] == ann_id and a["status"] == "deleted" for a in items)


# ─── auth ─────────────────────────────────────────────────────────────────────


def test_token_mode_blocks_unauthenticated_post(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_annotations(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "page")
        assert r.status_code == 401


def test_token_mode_allows_authenticated_post(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_annotations(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = client.post(
            "/api/annotations/page",
            json={"body": "ok", "selector": _SELECTOR},
            headers={"Authorization": "Bearer s3cret"},
        )
        assert r.status_code == 201


# ─── threading ────────────────────────────────────────────────────────────────


def test_replies_attach_to_parent(research_wiki_project: Path):
    _enable_annotations(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = _post_annotation(client, "page", body="parent")
        parent_id = r.json()["id"]

        r = _post_annotation(
            client, "page", body="reply", replies_to=parent_id
        )
        assert r.status_code == 201
        assert r.json()["replies_to"] == parent_id

        r = client.get("/api/annotations/page")
        items = r.json()
        ids = {(a["body"], a.get("replies_to")) for a in items}
        assert ("parent", None) in ids
        assert ("reply", parent_id) in ids
