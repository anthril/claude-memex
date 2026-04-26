"""Tests for the static exporter (Phase 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("starlette")
pytest.importorskip("mistune")
pytest.importorskip("yaml")
pytest.importorskip("httpx")

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite.exporter import export  # noqa: E402


def test_static_export_writes_html(research_wiki_project: Path, tmp_path: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    out = tmp_path / "dist"
    result = export(cfg, out_dir=out)
    assert (out / "index.html").is_file()
    # Each scaffolded markdown should be reachable as `<slug>/index.html`.
    assert (out / "AGENTS" / "index.html").is_file()
    # Static CSS should be copied verbatim.
    assert (out / "static" / "base.css").is_file()
    assert result.pages_written >= 3
    assert result.assets_copied >= 1


def test_static_export_marks_static_mode(research_wiki_project: Path, tmp_path: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    out = tmp_path / "dist"
    export(cfg, out_dir=out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "badge-static" in html


def test_static_export_writes_list_pages(research_wiki_project: Path, tmp_path: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    out = tmp_path / "dist"
    result = export(cfg, out_dir=out)
    # Read-only views for the dynamic list pages must exist post-export.
    for slug in ("open-questions", "rules", "comments"):
        target = out / slug / "index.html"
        assert target.is_file(), f"missing {target}"
    # The classic three (open-questions, rules, comments) plus the
    # profile-driven sections overview + per-section landing pages.
    assert result.list_pages_written >= 3
    assert (out / "sections" / "index.html").is_file()
    # research-wiki has an Entities section; per-section page must exist.
    assert (out / "sections" / "entities" / "index.html").is_file()


def test_static_export_list_pages_have_static_badge(research_wiki_project: Path, tmp_path: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    out = tmp_path / "dist"
    export(cfg, out_dir=out)
    html = (out / "open-questions" / "index.html").read_text(encoding="utf-8")
    assert "badge-static" in html
    # Submit buttons should be omitted in static mode (no `+ Submit` link).
    assert "+ Submit" not in html


def test_static_export_does_not_recurse_into_its_own_output(research_wiki_project: Path):
    """When the dist dir lives inside contentRoot, we must not walk it on the next pass."""
    import json
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": "."}
    cfg_path.write_text(json.dumps(raw))

    cfg = cfg_mod.load(start=research_wiki_project)
    out = research_wiki_project / "dist"
    first = export(cfg, out_dir=out)

    # Re-running the export must not see the previous run's output.
    second = export(cfg, out_dir=out)
    assert first.pages_written == second.pages_written, (
        "page count grew between runs — exporter is walking its own output"
    )
    assert first.folders_written == second.folders_written
