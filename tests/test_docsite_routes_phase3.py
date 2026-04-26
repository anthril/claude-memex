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


def test_open_questions_links_resolve_with_widened_content_root(
    research_wiki_project: Path,
):
    """Regression — when a project widens `docsite.contentRoot` (e.g. to ".")
    so the docsite serves the whole repo, open-question listing URLs must
    still resolve. Previously the URLs were built relative to `memex_root`
    (always `.memex/`) but the page handler routes against `wiki_root`
    (the widened root), producing 404s for every entry.
    """
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {
        "enabled": True,
        "writeFeatures": ["open-questions"],
        "contentRoot": ".",
    }
    cfg_path.write_text(json.dumps(raw))

    cfg = cfg_mod.load(start=research_wiki_project)
    # Sanity: contentRoot really did widen the wiki root.
    assert cfg.wiki_root == research_wiki_project.resolve()
    assert cfg.memex_root == (research_wiki_project / ".memex").resolve()

    with TestClient(make_app(cfg)) as client:
        # File a question via the API so we don't depend on fixture content.
        r = client.post(
            "/open-questions",
            data={"title": "Where do streams emit?", "body": "Investigating."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        listing = client.get("/open-questions")
        assert listing.status_code == 200
        # With contentRoot=".", URLs must include the .memex/ prefix so the
        # page handler — routing against wiki_root — can find the file.
        import re

        hrefs = re.findall(
            r'<a class="entry-title" href="([^"]+)"', listing.text
        )
        assert hrefs, "no open-question entries rendered"
        for href in hrefs:
            assert href.startswith("/.memex/.open-questions/"), (
                f"href {href!r} should be rooted at the widened wiki_root, "
                f"not the canonical memex_root"
            )
            page = client.get(href)
            assert page.status_code == 200, (
                f"GET {href} returned {page.status_code}; expected 200 — "
                f"this is the URL-routing bug fixed in 0.1.0-alpha.3."
            )


def test_open_questions_links_resolve_with_default_content_root(
    research_wiki_project: Path,
):
    """Companion to the contentRoot=. test — the default (no override) path
    must still produce `/.open-questions/...` URLs that resolve, since
    wiki_root == memex_root in that case."""
    _enable_writes(research_wiki_project)
    cfg = cfg_mod.load(start=research_wiki_project)
    assert cfg.wiki_root == cfg.memex_root

    with TestClient(make_app(cfg)) as client:
        r = client.post(
            "/open-questions",
            data={"title": "Default-root question", "body": "Investigating."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        listing = client.get("/open-questions")
        import re

        hrefs = re.findall(
            r'<a class="entry-title" href="([^"]+)"', listing.text
        )
        assert hrefs
        for href in hrefs:
            assert href.startswith("/.open-questions/")
            assert client.get(href).status_code == 200
