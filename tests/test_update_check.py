"""Tests for update-check.py + _lib/version.py.

Uses the `MEMEX_UPDATE_CHECK_JSON` fixture override so tests never touch
the network. Covers:
- SemVer compare edge cases
- Silent exit when updateCheck is off (default)
- Surface notice when a newer version is available
- Cache respects 24h TTL
- Graceful handling of malformed fixture data
"""
from __future__ import annotations

import json
from pathlib import Path

from _lib.version import CURRENT_VERSION, is_newer, parse_semver


class TestSemverCompare:
    def test_parse_plain(self):
        assert parse_semver("1.2.3") == (1, 2, 3, "")

    def test_parse_with_v_prefix(self):
        assert parse_semver("v1.2.3") == (1, 2, 3, "")

    def test_parse_with_prerelease(self):
        assert parse_semver("1.2.3-alpha.1") == (1, 2, 3, "alpha.1")
        assert parse_semver("0.1.0-alpha.1") == (0, 1, 0, "alpha.1")

    def test_parse_invalid(self):
        assert parse_semver("") is None
        assert parse_semver("not-a-version") is None
        assert parse_semver("1.2") is None

    def test_is_newer_major(self):
        assert is_newer("2.0.0", "1.9.9")
        assert not is_newer("1.0.0", "2.0.0")

    def test_is_newer_minor(self):
        assert is_newer("1.2.0", "1.1.9")
        assert not is_newer("1.1.0", "1.2.0")

    def test_is_newer_patch(self):
        assert is_newer("1.0.1", "1.0.0")

    def test_is_newer_same_returns_false(self):
        assert not is_newer("1.0.0", "1.0.0")

    def test_release_beats_prerelease_same_core(self):
        assert is_newer("0.1.0", "0.1.0-alpha.1")
        assert not is_newer("0.1.0-alpha.1", "0.1.0")

    def test_prerelease_compare(self):
        assert is_newer("0.1.0-alpha.2", "0.1.0-alpha.1")
        assert not is_newer("0.1.0-alpha.1", "0.1.0-alpha.2")

    def test_invalid_returns_false(self):
        assert not is_newer("not-a-version", "1.0.0")
        assert not is_newer("1.0.0", "not-a-version")

    def test_current_version_is_parseable(self):
        """The plugin's own version must parse — otherwise update checks silently fail."""
        assert parse_semver(CURRENT_VERSION) is not None, \
            f"CURRENT_VERSION={CURRENT_VERSION!r} must be SemVer"


def _enable_update_check(project_root: Path, fixture_version: str = "9.9.9") -> Path:
    """Enable updateCheck in config + set up the fixture file with given version."""
    cfg_path = project_root / "memex.config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg.setdefault("hookEvents", {}).setdefault("sessionStart", {})["updateCheck"] = True
    cfg_path.write_text(json.dumps(cfg))

    fixture = project_root / "update-check-fixture.json"
    fixture.write_text(json.dumps({
        "tag_name": f"v{fixture_version}",
        "html_url": f"https://github.com/anthril/claude-memex/releases/tag/v{fixture_version}",
    }))
    return fixture


class TestUpdateCheckHook:
    def test_silent_when_not_opted_in(self, engineering_ops_project, run_hook, monkeypatch):
        # Default: updateCheck absent → hook exits silently, no network call
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", "")
        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert not out.strip(), "should emit no context when opt-in flag is off"

    def test_surfaces_notice_when_newer_available(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="9.9.9")
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert out.strip(), "should emit additionalContext when newer version exists"
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "update available" in ctx.lower()
        assert "9.9.9" in ctx
        assert CURRENT_VERSION in ctx

    def test_silent_when_not_newer(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="0.0.1")
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert not out.strip()

    def test_cache_respects_ttl(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="9.9.9")
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        cache_path = engineering_ops_project / ".memex" / ".state" / "update-check.json"

        # First run populates cache
        rc, _, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert cache_path.exists()
        first_cache = json.loads(cache_path.read_text())
        assert first_cache["latest_version"] == "9.9.9"

        # Second run: change fixture to a different version. Cache should still return 9.9.9
        # because TTL hasn't elapsed.
        fixture.write_text(json.dumps({"tag_name": "v5.5.5", "html_url": "..."}))
        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "9.9.9" in ctx  # cached value, not the new fixture
        assert "5.5.5" not in ctx

    def test_cache_refetches_after_ttl_expired(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="9.9.9")
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        cache_path = engineering_ops_project / ".memex" / ".state" / "update-check.json"
        # Populate cache with a stale timestamp
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "checked_at": 0,  # 1970 — very much expired
            "latest_version": "1.1.1",
            "latest_url": "https://example.com/old",
            "current_version": CURRENT_VERSION,
        }))

        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        # Expired cache → should re-fetch from fixture and see 9.9.9
        assert "9.9.9" in ctx
        assert "1.1.1" not in ctx

    def test_graceful_on_malformed_fixture(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="9.9.9")
        fixture.write_text("not valid json {{")
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        # Should silently exit rather than error
        rc, out, err = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert not out.strip()

    def test_graceful_when_tag_missing(self, engineering_ops_project, run_hook, monkeypatch):
        fixture = _enable_update_check(engineering_ops_project, fixture_version="9.9.9")
        fixture.write_text(json.dumps({"html_url": "..."}))  # no tag_name
        monkeypatch.setenv("MEMEX_UPDATE_CHECK_JSON", str(fixture))

        rc, out, _ = run_hook("update-check.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        assert not out.strip()

    def test_silent_outside_memex_project(self, tmp_path, run_hook):
        """No config → no check, no noise."""
        rc, out, _ = run_hook("update-check.py", {"cwd": str(tmp_path)})
        assert rc == 0
        assert not out.strip()
