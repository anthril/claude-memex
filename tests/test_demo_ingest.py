"""Contract tests for examples/research-wiki-demo/.

The demo folder is a fully-realised post-ingest wiki. This test verifies
every claim the WALKTHROUGH makes — each page has valid frontmatter, each
cross-reference resolves, the index catalogues every page, the log has the
parseable ingest entry.

Breakage here means the demo is out of sync with the ingest-source skill
contract.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "examples" / "research-wiki-demo"
MEMEX = DEMO / ".memex"

EXPECTED_PAGES = {
    "wiki/summaries/transformer-circuits.md": "summary",
    "wiki/entities/anthropic/README.md": "entity",
    "wiki/concepts/mechanistic-interpretability/README.md": "concept",
    "wiki/concepts/induction-heads/README.md": "concept",
    ".open-questions/how-does-induction-work-at-scale.md": "open-question",
}


def read(rel: str) -> str:
    return (MEMEX / rel).read_text(encoding="utf-8")


class TestDemoStructure:
    def test_demo_directory_exists(self):
        assert DEMO.exists()
        assert MEMEX.exists()
        assert (DEMO / "memex.config.json").exists()
        assert (DEMO / "WALKTHROUGH.md").exists()

    def test_source_file_present(self):
        assert (MEMEX / "raw" / "articles" / "transformer-circuits.md").exists()

    @pytest.mark.parametrize("rel,expected_type", EXPECTED_PAGES.items())
    def test_expected_page_exists(self, rel, expected_type):
        assert (MEMEX / rel).exists(), f"demo missing {rel}"

    def test_index_exists(self):
        assert (MEMEX / "index.md").exists()

    def test_log_exists(self):
        assert (MEMEX / "log.md").exists()


class TestFrontmatterValidity:
    """Every generated wiki page carries the research-wiki profile's required fields."""

    REQUIRED = ["title", "slug", "type", "status", "created", "updated"]

    @pytest.mark.parametrize("rel,expected_type", EXPECTED_PAGES.items())
    def test_page_has_required_frontmatter(self, rel, expected_type):
        from _lib.frontmatter import parse
        content = read(rel)
        fm = parse(content)
        assert fm is not None, f"{rel}: no frontmatter"
        for field in self.REQUIRED:
            assert fm.get(field), f"{rel}: missing `{field}`"
        assert fm["type"] == expected_type, f"{rel}: type={fm['type']}, expected {expected_type}"

    def test_slug_matches_filename(self):
        """A page's slug should match its file's stem (or parent folder for README.md pages)."""
        from _lib.frontmatter import parse
        for rel in EXPECTED_PAGES:
            fm = parse(read(rel)) or {}
            fname = Path(rel).name
            expected_slug = Path(rel).parent.name if fname == "README.md" else Path(rel).stem
            assert fm.get("slug") == expected_slug, \
                f"{rel}: slug={fm.get('slug')}, expected {expected_slug}"


class TestCrossReferences:
    """Each generated page must link back to its origin + related pages."""

    def test_summary_references_all_extracted_pages(self):
        summary = read("wiki/summaries/transformer-circuits.md")
        # Should wikilink the entity and both concepts
        assert "[[anthropic]]" in summary
        assert "[[mechanistic-interpretability]]" in summary
        assert "[[induction-heads]]" in summary

    def test_entity_references_source(self):
        content = read("wiki/entities/anthropic/README.md")
        assert "transformer-circuits" in content, "entity must reference its origin summary"

    def test_concepts_reference_source(self):
        for c in ("mechanistic-interpretability", "induction-heads"):
            content = read(f"wiki/concepts/{c}/README.md")
            assert "transformer-circuits" in content, \
                f"{c}: must reference source summary"

    def test_concept_interconnection(self):
        """induction-heads should link to mechanistic-interpretability and vice versa."""
        induction = read("wiki/concepts/induction-heads/README.md")
        mi = read("wiki/concepts/mechanistic-interpretability/README.md")
        assert "[[mechanistic-interpretability]]" in induction
        assert "[[induction-heads]]" in mi

    def test_open_question_references_source(self):
        q = read(".open-questions/how-does-induction-work-at-scale.md")
        assert "[[transformer-circuits]]" in q or "transformer-circuits" in q


class TestIndexCatalog:
    """The index must reference every generated wiki page."""

    def test_index_has_expected_sections(self):
        idx = read("index.md")
        for section in ("## Entities", "## Concepts", "## Summaries", "## Open Questions"):
            assert section in idx, f"index missing {section}"

    @pytest.mark.parametrize("rel,_type", EXPECTED_PAGES.items())
    def test_index_references_page(self, rel, _type):
        from _lib.index_parse import flatten, parse_index
        idx_content = read("index.md")
        sections = parse_index(idx_content)
        all_refs = flatten(sections)
        # Match either the full relative path or the slug
        slug = Path(rel).parent.name if Path(rel).name == "README.md" else Path(rel).stem
        found = any(rel in ref or ref.endswith(Path(rel).name) or slug == ref for ref in all_refs)
        assert found, f"index has no entry pointing at {rel} (or slug {slug})"


class TestLogEntries:
    def test_log_has_init_entry(self):
        log = read("log.md")
        assert re.search(r"^## \[2026-04-\d\d\] init \|", log, re.MULTILINE), \
            "log missing init entry"

    def test_log_has_ingest_entry(self):
        log = read("log.md")
        assert re.search(r"^## \[\d{4}-\d{2}-\d{2}\] ingest \| transformer-circuits", log, re.MULTILINE), \
            "log missing transformer-circuits ingest entry"

    def test_log_entries_use_parseable_prefix(self):
        """`grep '^## \\[' log.md | tail -5` must work — see CREDITS.md / llm-wiki.md pattern."""
        log = read("log.md")
        entries = re.findall(r"^## \[\d{4}-\d{2}-\d{2}\] \w+ \| ", log, re.MULTILINE)
        assert len(entries) >= 2, f"expected >=2 parseable log entries, got {len(entries)}"


class TestHooksAcceptDemo:
    """Running the real plugin hooks against the demo must produce no violations."""

    def test_path_guard_accepts_every_page(self, run_hook):
        for rel in EXPECTED_PAGES:
            target = MEMEX / rel.replace("/", "\\" if False else "/")  # os-independent
            target = MEMEX
            for part in rel.split("/"):
                target = target / part
            rc, _, err = run_hook("path-guard.py", {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            })
            assert rc == 0, f"path-guard rejected {rel}: {err}"

    @pytest.mark.parametrize("rel,_type", EXPECTED_PAGES.items())
    def test_frontmatter_check_accepts_each_page(self, rel, _type, run_hook):
        target = MEMEX
        for part in rel.split("/"):
            target = target / part
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, f"frontmatter-check rejected {rel}: {err}"
