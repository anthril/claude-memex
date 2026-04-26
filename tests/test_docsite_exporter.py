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
    assert result.list_pages_written == 3


def test_static_export_list_pages_have_static_badge(research_wiki_project: Path, tmp_path: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    out = tmp_path / "dist"
    export(cfg, out_dir=out)
    html = (out / "open-questions" / "index.html").read_text(encoding="utf-8")
    assert "badge-static" in html
    # Submit buttons should be omitted in static mode (no `+ Submit` link).
    assert "+ Submit" not in html
