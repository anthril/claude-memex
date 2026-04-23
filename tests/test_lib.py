"""Unit tests on hooks/scripts/_lib/* — pure functions."""
import re

from _lib.config import DEFAULT_CONFIG, _deep_merge
from _lib.frontmatter import parse, validate
from _lib.index_parse import contains_reference, parse_index, suggest_section
from _lib.paths import is_dated_folder, is_kebab_filename, is_kebab_segment, normalise
from _lib.patterns import glob_to_regex, substitute


class TestPaths:
    def test_is_kebab_segment_accepts(self):
        assert is_kebab_segment("my-slug")
        assert is_kebab_segment("a")
        assert is_kebab_segment("a123")
        assert is_kebab_segment("one-two-three")

    def test_is_kebab_segment_rejects(self):
        assert not is_kebab_segment("MySlug")
        assert not is_kebab_segment("my_slug")
        assert not is_kebab_segment("my slug")
        assert not is_kebab_segment("-starts-with-hyphen")
        assert not is_kebab_segment("ends-with-hyphen-")
        assert not is_kebab_segment("double--hyphen")

    def test_is_kebab_filename(self):
        assert is_kebab_filename("foo-bar.md")
        assert is_kebab_filename("01-foo-bar.md")
        assert is_kebab_filename("a.md")
        assert not is_kebab_filename("Foo-Bar.md")
        assert not is_kebab_filename("foo_bar.md")

    def test_is_dated_folder(self):
        assert is_dated_folder("22042026-1000")
        assert is_dated_folder("01012020-0000")
        assert not is_dated_folder("2026-04-22")
        assert not is_dated_folder("22042026")
        assert not is_dated_folder("22042026-10:00")  # colon NTFS-breaker

    def test_normalise(self):
        assert normalise("C:\\foo\\bar") == "C:/foo/bar"
        assert normalise("already/forward") == "already/forward"


class TestFrontmatter:
    def test_parse_simple(self):
        content = "---\ntitle: Foo\nslug: foo\n---\n\nbody"
        fm = parse(content)
        assert fm == {"title": "Foo", "slug": "foo"}

    def test_parse_none_when_missing(self):
        assert parse("no frontmatter here") is None

    def test_parse_strips_quotes(self):
        content = "---\ntitle: 'Quoted Title'\n---\n"
        assert parse(content)["title"] == "Quoted Title"

    def test_parse_ignores_comments(self):
        content = "---\n# comment\ntitle: Foo\n---\n"
        assert parse(content) == {"title": "Foo"}

    def test_validate_ok(self):
        content = "---\ntitle: x\nslug: y\n---\nbody"
        ok, msg = validate(content, ["title", "slug"])
        assert ok, msg

    def test_validate_missing_field(self):
        content = "---\ntitle: x\n---\nbody"
        ok, msg = validate(content, ["title", "slug"])
        assert not ok
        assert "slug" in msg

    def test_validate_enum_rejects(self):
        content = "---\ntitle: x\nstatus: bogus\n---\n"
        ok, msg = validate(content, ["title"], {"status": ["active", "draft"]})
        assert not ok
        assert "bogus" in msg

    def test_validate_enum_accepts(self):
        content = "---\ntitle: x\nstatus: active\n---\n"
        ok, _ = validate(content, ["title"], {"status": ["active", "draft"]})
        assert ok


class TestIndexParse:
    SAMPLE = """# Index

## Entities

- [Foo](entities/foo/README.md)
- [Bar](entities/bar/README.md)

## Concepts

*No concepts yet.*

## Recent Activity

- some freeform thing
- [[baz-slug]]
"""

    def test_parse_index_sections(self):
        sections = parse_index(self.SAMPLE)
        assert "Entities" in sections
        assert "Concepts" in sections
        assert "Recent Activity" in sections

    def test_parse_index_extracts_links(self):
        sections = parse_index(self.SAMPLE)
        assert "entities/foo/README.md" in sections["Entities"]
        assert "entities/bar/README.md" in sections["Entities"]
        assert "baz-slug" in sections["Recent Activity"]

    def test_parse_index_empty_sections(self):
        sections = parse_index(self.SAMPLE)
        assert sections["Concepts"] == set()

    def test_contains_reference_true_for_path(self):
        sections = parse_index(self.SAMPLE)
        assert contains_reference(sections, "entities/foo/README.md", "foo")

    def test_contains_reference_true_for_wikilink_slug(self):
        sections = parse_index(self.SAMPLE)
        assert contains_reference(sections, "analyses/baz-slug.md", "baz-slug")

    def test_contains_reference_false_when_absent(self):
        sections = parse_index(self.SAMPLE)
        assert not contains_reference(sections, "entities/new/README.md", "new")

    def test_suggest_section_by_type(self):
        sections = parse_index(self.SAMPLE)
        assert suggest_section(sections, "entities/foo/README.md", "entity") == "Entities"
        assert suggest_section(sections, "concepts/x/README.md", "concept") == "Concepts"

    def test_suggest_section_by_folder(self):
        sections = parse_index(self.SAMPLE)
        # No page_type, but first folder `entities/` matches "Entities"
        assert suggest_section(sections, "entities/new/README.md", None) == "Entities"

    def test_suggest_section_none_when_no_match(self):
        sections = parse_index(self.SAMPLE)
        assert suggest_section(sections, "unrelated/x.md", None) is None


class TestConfig:
    def test_deep_merge_overrides(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99}}
        merged = _deep_merge(base, override)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 99
        assert merged["b"]["d"] == 3

    def test_default_config_has_required_keys(self):
        assert "root" in DEFAULT_CONFIG
        assert "allowedTopLevel" in DEFAULT_CONFIG
        assert "frontmatter" in DEFAULT_CONFIG
        assert "required" in DEFAULT_CONFIG["frontmatter"]


class TestPatterns:
    def test_glob_to_regex_single_star(self):
        rx = glob_to_regex("src/features/*/")
        m = re.match("^" + rx + "$", "src/features/auth/")
        assert m is not None
        assert m.groups() == ("auth",)

    def test_glob_to_regex_double_star(self):
        rx = glob_to_regex("deep/**/file.ts")
        m = re.match("^" + rx + "$", "deep/a/b/c/file.ts")
        assert m is not None
        assert m.groups() == ("a/b/c",)

    def test_glob_to_regex_single_star_rejects_slash(self):
        """`*` must not match `/` — only `**` does."""
        rx = glob_to_regex("src/*/index.ts")
        assert re.match("^" + rx + "$", "src/auth/index.ts")
        assert not re.match("^" + rx + "$", "src/auth/nested/index.ts")

    def test_glob_to_regex_escapes_regex_meta(self):
        rx = glob_to_regex("supabase/migrations/*.sql")
        # `.` must be escaped so "sql.sql" doesn't match "*.sql" loosely
        m = re.match("^" + rx + "$", "supabase/migrations/init.sql")
        assert m is not None
        # A literal `.` in the target must match the escaped `.` in the pattern
        assert re.match("^" + rx + "$", "supabase/migrations/20240101000000_init.sql")

    def test_glob_to_regex_literal_parens_escaped(self):
        """Important for Next.js App Router groups: `(dashboard)`."""
        rx = glob_to_regex("src/app/(dashboard)/*/")
        m = re.match("^" + rx + "$", "src/app/(dashboard)/settings/")
        assert m is not None
        assert m.groups() == ("settings",)

    def test_substitute_single_group(self):
        assert substitute("platform/features/{1}/README.md", ["auth"]) == \
            "platform/features/auth/README.md"

    def test_substitute_multiple_groups(self):
        assert substitute("{1}/{2}/README.md", ["platform", "features"]) == \
            "platform/features/README.md"

    def test_substitute_out_of_range_leaves_placeholder(self):
        assert substitute("{1}/{5}", ["a"]) == "a/{5}"

    def test_substitute_no_placeholders(self):
        assert substitute("no/placeholders/here", ["auth"]) == "no/placeholders/here"
