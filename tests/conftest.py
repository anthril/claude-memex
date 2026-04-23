"""Shared pytest fixtures.

Every test that exercises a hook gets a freshly-scaffolded project in a
tmp_path. Request the `project(<profile>)` fixture or one of the
named-profile shortcuts (`engineering_ops_project`, `research_wiki_project`, etc.).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks" / "scripts"
PROFILES_DIR = REPO_ROOT / "templates" / "profiles"
PROFILES = ("engineering-ops", "research-wiki", "book-companion", "personal-journal", "generic")

# Make `_lib.*` importable by test modules at collection time (before any fixtures run).
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def _scaffold(profile: str, dst: Path) -> Path:
    """Copy a profile's files into `dst` and drop .keep files."""
    src = PROFILES_DIR / profile
    shutil.copy(src / "memex.config.json", dst / "memex.config.json")
    shutil.copytree(src / ".memex", dst / ".memex")
    shutil.copy(src / "CLAUDE.md", dst / "CLAUDE.md")
    for root, _dirs, files in os.walk(dst / ".memex"):
        for f in files:
            if f == ".keep":
                os.remove(Path(root) / f)
    return dst


@pytest.fixture
def project(tmp_path):
    """Factory: call `project('engineering-ops')` to scaffold and return the path."""
    def _make(profile: str) -> Path:
        assert profile in PROFILES, f"unknown profile {profile}"
        return _scaffold(profile, tmp_path)
    return _make


@pytest.fixture
def engineering_ops_project(tmp_path):
    return _scaffold("engineering-ops", tmp_path)


@pytest.fixture
def research_wiki_project(tmp_path):
    return _scaffold("research-wiki", tmp_path)


@pytest.fixture
def generic_project(tmp_path):
    return _scaffold("generic", tmp_path)


@pytest.fixture
def book_companion_project(tmp_path):
    return _scaffold("book-companion", tmp_path)


@pytest.fixture
def personal_journal_project(tmp_path):
    return _scaffold("personal-journal", tmp_path)


@pytest.fixture
def run_hook():
    """Invoke a hook script with a JSON payload; return (rc, stdout, stderr)."""
    def _run(script: str, payload: dict, cwd: str | None = None):
        p = subprocess.run(
            [sys.executable, str(HOOKS_DIR / script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
        return p.returncode, p.stdout, p.stderr
    return _run


@pytest.fixture(autouse=True)
def _add_lib_to_path(monkeypatch):
    """Make `_lib` importable for unit tests in test_lib.py."""
    monkeypatch.syspath_prepend(str(HOOKS_DIR))
