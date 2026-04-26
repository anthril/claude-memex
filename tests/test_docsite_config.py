"""Tests for `memex_docsite.config` (Phase 1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import config as cfg_mod  # noqa: E402


def test_load_defaults_when_no_docsite_block(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    assert cfg.enabled is True
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.auth == "none"
    assert cfg.show_hidden is True
    assert cfg.write_features == []
    assert cfg.wiki_root == (research_wiki_project / ".memex").resolve()


def test_load_reads_docsite_block(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {
        "enabled": True,
        "port": 9000,
        "auth": "token",
        "title": "Hello",
        "showHidden": False,
        "writeFeatures": ["open-questions", "annotations"],
        "annotations": {"defaultVisibility": "group", "allowAnonymous": False},
    }
    cfg_path.write_text(json.dumps(raw))

    cfg = cfg_mod.load(start=research_wiki_project)
    assert cfg.port == 9000
    assert cfg.auth == "token"
    assert cfg.title == "Hello"
    assert cfg.show_hidden is False
    assert cfg.write_features == ["open-questions", "annotations"]
    assert cfg.annotations.default_visibility == "group"
    assert cfg.annotations.allow_anonymous is False


def test_invalid_auth_rejected(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"auth": "bogus"}
    cfg_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="auth must be one of"):
        cfg_mod.load(start=research_wiki_project)


def test_missing_config_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        cfg_mod.load(start=tmp_path)


def test_content_root_override_widens_wiki_root(research_wiki_project: Path):
    """`docsite.contentRoot` lets the docsite walk a wider tree than `.memex/`."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": "."}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    # wiki_root is now the project root, not .memex/.
    assert cfg.wiki_root == research_wiki_project.resolve()


def test_content_root_override_resolves_relative(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": ".memex/wiki"}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    assert cfg.wiki_root == (research_wiki_project / ".memex" / "wiki").resolve()


def test_content_root_rejects_non_string(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": ["."]}
    cfg_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="contentRoot"):
        cfg_mod.load(start=research_wiki_project)


def test_is_ignored_matches_top_level(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"ignorePatterns": ["docs-site/**", "node_modules/**"]}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    assert cfg.is_ignored("docs-site/index.md") is True
    assert cfg.is_ignored("docs-site/content/page.md") is True
    assert cfg.is_ignored("node_modules/foo/bar.md") is True
    assert cfg.is_ignored("architecture/concept.md") is False


def test_is_ignored_matches_nested_segments(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"ignorePatterns": ["__pycache__/**"]}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    # `__pycache__` anywhere in the tree should match.
    assert cfg.is_ignored("foo/__pycache__/bar.md") is True
    assert cfg.is_ignored("__pycache__/bar.md") is True
    assert cfg.is_ignored("normal/path.md") is False


def test_is_ignored_empty_when_no_patterns(research_wiki_project: Path):
    """A user with no `ignorePatterns` still gets the default `.state/sessions/**`
    suppression so PreCompact session snapshots don't appear in the docsite tree.
    """
    cfg = cfg_mod.load(start=research_wiki_project)
    assert ".state/sessions/**" in cfg.ignore_patterns
    assert cfg.is_ignored("anything.md") is False
    assert cfg.is_ignored(".state/sessions/abc.md") is True


def test_user_ignore_patterns_merge_with_defaults(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"ignorePatterns": ["build/**"]}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    assert "build/**" in cfg.ignore_patterns
    # Default still present.
    assert ".state/sessions/**" in cfg.ignore_patterns
