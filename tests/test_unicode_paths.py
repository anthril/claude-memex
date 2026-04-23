"""Tests for Unicode kebab-case support.

Verifies:
- Unicode-friendly mode (default) accepts lowercase/caseless letters from any
  script: Japanese, Greek, Cyrillic, Arabic, Hebrew, Chinese, Korean, Thai, etc.
- ASCII mode (`naming.asciiOnly: true`) still rejects the same inputs
- Both modes reject genuine violations: uppercase, spaces, consecutive hyphens,
  underscores
- Extensions stay ASCII even in Unicode mode (file-system portability)
"""
from __future__ import annotations

import json

import pytest
from _lib.paths import is_kebab_filename, is_kebab_segment

# Representative slugs across writing systems — all should be valid kebab
# segments in Unicode mode.
UNICODE_SEGMENTS = [
    # Japanese (hiragana, katakana, kanji — all Lo/Ll)
    "こんにちは",
    "きょうと",
    "東京",
    # Greek — lowercase Ll
    "αγορά",
    "φιλοσοφία",
    # Cyrillic — lowercase Ll
    "москва",
    "санкт-петербург",
    # Arabic — Lo, no case
    "مرحبا",
    # Hebrew — Lo, no case
    "שלום",
    # Chinese — Lo
    "北京",
    # Korean — Lo
    "서울",
    # Thai — Lo
    "กรุงเทพ",
    # Mixed Unicode + hyphen + digit
    "東京-2024",
    "москва-01",
    # ASCII still works
    "my-entity",
    "foo-bar-baz",
    "a1",
]


class TestUnicodeMode:
    """Default: unicode_ok=True accepts scripts with no case or lowercase-only."""

    @pytest.mark.parametrize("seg", UNICODE_SEGMENTS)
    def test_unicode_segment_accepted(self, seg):
        assert is_kebab_segment(seg, unicode_ok=True), f"should accept Unicode slug: {seg!r}"

    def test_unicode_rejects_uppercase_ascii(self):
        assert not is_kebab_segment("MySlug", unicode_ok=True)

    def test_unicode_rejects_greek_uppercase(self):
        # Ά (Greek alpha with tonos, Lu) should be rejected
        assert not is_kebab_segment("Αγορά", unicode_ok=True)

    def test_unicode_rejects_cyrillic_uppercase(self):
        assert not is_kebab_segment("Москва", unicode_ok=True)

    def test_unicode_rejects_space(self):
        assert not is_kebab_segment("東京 kyoto", unicode_ok=True)

    def test_unicode_rejects_underscore(self):
        assert not is_kebab_segment("東京_kyoto", unicode_ok=True)

    def test_unicode_rejects_leading_hyphen(self):
        assert not is_kebab_segment("-東京", unicode_ok=True)

    def test_unicode_rejects_trailing_hyphen(self):
        assert not is_kebab_segment("東京-", unicode_ok=True)

    def test_unicode_rejects_consecutive_hyphens(self):
        assert not is_kebab_segment("東京--kyoto", unicode_ok=True)

    def test_unicode_rejects_symbols(self):
        assert not is_kebab_segment("東京!", unicode_ok=True)
        assert not is_kebab_segment("東京@kyoto", unicode_ok=True)


class TestAsciiMode:
    """ASCII-only mode rejects all non-ASCII scripts."""

    @pytest.mark.parametrize("seg", [
        "東京", "αγορά", "москва", "مرحبا", "שלום",
    ])
    def test_ascii_mode_rejects_unicode(self, seg):
        assert not is_kebab_segment(seg, unicode_ok=False)

    def test_ascii_mode_still_accepts_ascii(self):
        assert is_kebab_segment("my-entity", unicode_ok=False)
        assert is_kebab_segment("a1-b2-c3", unicode_ok=False)


class TestUnicodeFilenames:
    def test_unicode_filename_ok(self):
        assert is_kebab_filename("東京.md", unicode_ok=True)
        assert is_kebab_filename("αγορά.md", unicode_ok=True)

    def test_unicode_with_ordering_prefix(self):
        assert is_kebab_filename("01-東京.md", unicode_ok=True)
        assert is_kebab_filename("42-москва-01.md", unicode_ok=True)

    def test_ascii_extension_required(self):
        """Extensions stay ASCII even in Unicode mode — portability."""
        # A filename with a non-ASCII extension should be rejected
        # because the extension regex is ASCII-only.
        assert not is_kebab_filename("東京.日本語", unicode_ok=True)

    def test_ascii_mode_rejects_unicode_filename(self):
        assert not is_kebab_filename("東京.md", unicode_ok=False)


class TestHookIntegration:
    """End-to-end: path-guard respects the config flag."""

    def _cfg_with_ascii_only(self, project, ascii_only):
        cfg_path = project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg.setdefault("naming", {})["asciiOnly"] = ascii_only
        cfg_path.write_text(json.dumps(cfg))

    def test_default_accepts_japanese_entity(self, engineering_ops_project, run_hook):
        # Default config has no asciiOnly key — should default to Unicode-friendly
        target = engineering_ops_project / ".memex" / "entities" / "東京" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, f"default should accept Japanese slug: {err}"

    def test_default_accepts_greek_concept(self, research_wiki_project, run_hook):
        target = research_wiki_project / ".memex" / "wiki" / "concepts" / "φιλοσοφία" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, f"default should accept Greek slug: {err}"

    def test_ascii_only_rejects_japanese(self, engineering_ops_project, run_hook):
        self._cfg_with_ascii_only(engineering_ops_project, True)
        target = engineering_ops_project / ".memex" / "entities" / "東京" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 2
        assert "ASCII-only" in err

    def test_ascii_only_still_accepts_ascii(self, engineering_ops_project, run_hook):
        self._cfg_with_ascii_only(engineering_ops_project, True)
        target = engineering_ops_project / ".memex" / "entities" / "my-entity" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, f"ASCII slug should still be accepted in ascii-only mode: {err}"

    def test_unicode_mode_still_rejects_uppercase(self, engineering_ops_project, run_hook):
        # Default mode — still rejects UPPERCASE because we only accept Ll/Lo
        target = engineering_ops_project / ".memex" / "entities" / "UPPER-case" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 2
        assert "not kebab-case" in err
