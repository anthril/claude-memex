"""Tests for the open-questions + rules HTTP routes (Phase 3)."""
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


def _enable_writes(project: Path, *, auth: str = "none") -> Path:
    """Set the project's docsite config to enable both write features."""
    cfg_path = project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {
        "enabled": True,
        "auth": auth,
        "writeFeatures": ["open-questions", "rules"],
    }
    cfg_path.write_text(json.dumps(raw))
    return project


def _client(project_path: Path) -> TestClient:
    cfg = cfg_mod.load(start=project_path)
    return TestClient(make_app(cfg))


# ─── open-questions ────────────────────────────────────────────────────────────


def test_open_questions_list_renders(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.get("/open-questions")
        assert r.status_code == 200
        assert "Open questions" in r.text
        assert "+ Submit" in r.text  # write_enabled = True


def test_open_questions_form_renders(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.get("/open-questions/new")
        assert r.status_code == 200
        assert "Submit an open question" in r.text


def test_open_questions_form_404_when_writes_disabled(research_wiki_project: Path):
    # Default config has write_features = []
    with _client(research_wiki_project) as client:
        r = client.get("/open-questions/new")
        assert r.status_code == 404


def test_open_questions_post_creates_file(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/open-questions",
            data={
                "title": "Where does decision tracking live?",
                "body": "Looking for the canonical place to log architecture decisions.",
                "author": "alice",
                "owner": "alice",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert "/open-questions/" in r.headers["location"]

    # Confirm a file was actually written (the scaffold ships a README.md
    # under `.open-questions/` so filter to non-README files).
    folder = research_wiki_project / ".memex" / ".open-questions"
    new_files = [p for p in folder.glob("*.md") if p.name != "README.md"]
    assert len(new_files) == 1
    assert "decision-tracking" in new_files[0].name or "where-does" in new_files[0].name


def test_open_questions_post_rejects_empty_fields(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post("/open-questions", data={"title": "", "body": ""})
        assert r.status_code == 200
        assert "Title and body are required" in r.text


def test_open_questions_resolve_post_moves_file(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/open-questions",
            data={"title": "Foo", "body": "Bar", "author": "alice"},
            follow_redirects=False,
        )
        assert r.status_code == 303
        slug = r.headers["location"].rsplit("/", 1)[-1]

        r = client.post(f"/open-questions/{slug}/resolve", follow_redirects=False)
        assert r.status_code == 303

    # The active file should now be in `.resolved/`.
    folder = research_wiki_project / ".memex" / ".open-questions"
    assert not (folder / f"{slug}.md").is_file()
    assert (folder / ".resolved" / f"{slug}.md").is_file()


def test_open_questions_post_token_mode_blocks_unauthenticated(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_writes(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = client.post("/open-questions", data={"title": "x", "body": "y"})
        assert r.status_code == 401


def test_open_questions_post_token_mode_allows_with_form_token(
    research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMEX_DOCSITE_TOKEN", "s3cret")
    _enable_writes(research_wiki_project, auth="token")
    with _client(research_wiki_project) as client:
        r = client.post(
            "/open-questions",
            data={"title": "Foo", "body": "Bar", "_memex_token": "s3cret"},
            follow_redirects=False,
        )
        assert r.status_code == 303


# ─── rules ─────────────────────────────────────────────────────────────────────


def test_rules_list_renders(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.get("/rules")
        assert r.status_code == 200
        assert "Rules" in r.text


def test_rules_post_creates_file(research_wiki_project: Path):
    _enable_writes(research_wiki_project)
    with _client(research_wiki_project) as client:
        r = client.post(
            "/rules",
            data={
                "title": "Always cite sources",
                "body": "Provenance hash per claim.",
                "author": "alice",
                "scope": "wiki/**",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303

    folder = research_wiki_project / ".memex" / ".rules"
    files = list(folder.glob("*.md"))
    # `.rules/` already had a README.md from the scaffold; the new rule is one extra file.
    new_files = [f for f in files if "always-cite" in f.name or "cite" in f.name.lower()]
    assert len(new_files) == 1


def test_rules_post_404_when_writes_disabled(research_wiki_project: Path):
    with _client(research_wiki_project) as client:
        r = client.post(
            "/rules", data={"title": "x", "body": "y"}, follow_redirects=False
        )
        assert r.status_code == 404
