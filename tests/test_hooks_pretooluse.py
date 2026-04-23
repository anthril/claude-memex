"""PreToolUse hooks: path-guard, readme-required, doc-required, ingest-doc-link, frontmatter-precheck."""
from __future__ import annotations

import json


class TestPathGuard:
    def test_rejects_unknown_top_level(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "scratchpad" / "note.md")},
        })
        assert rc == 2
        assert "not a permitted top-level" in err

    def test_accepts_valid_kebab_slug(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "entities" / "my-entity" / "README.md")},
        })
        assert rc == 0, err

    def test_rejects_camelcase_folder(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "entities" / "MyEntity" / "README.md")},
        })
        assert rc == 2
        assert "not kebab-case" in err

    def test_rejects_colon_in_dated_folder(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / ".audits" / "2026-04-23T10:00" / "README.md")},
        })
        assert rc == 2
        assert "Colon in path segment" in err

    def test_accepts_valid_dated_format(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / ".audits" / "23042026-1000" / "README.md")},
        })
        assert rc == 0, err

    def test_rejects_wrong_dated_format(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / ".audits" / "2026-04-23-1000" / "README.md")},
        })
        assert rc == 2
        assert "must match" in err

    def test_rejects_non_kebab_filename(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "entities" / "foo" / "MyDocs.md")},
        })
        assert rc == 2
        assert "not kebab-case" in err

    def test_silent_outside_ops_root(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / "src" / "MyFile.ts")},
        })
        # path is outside .memex/, so we let it through silently
        assert rc == 0


class TestReadmeRequired:
    def test_blocks_non_readme_in_empty_slug(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("readme-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "platform" / "features" / "new" / "details.md")},
        })
        assert rc == 2
        assert "has no README" in err

    def test_allows_readme_as_first_write(self, engineering_ops_project, run_hook):
        rc, _, err = run_hook("readme-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "platform" / "features" / "new" / "README.md")},
        })
        assert rc == 0, err

    def test_allows_non_readme_if_readme_exists(self, engineering_ops_project, run_hook):
        readme = engineering_ops_project / ".memex" / "entities" / "sample" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text("---\ntitle: Sample\nslug: sample\n---\n", encoding="utf-8")
        rc, _, err = run_hook("readme-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(readme.parent / "details.md")},
        })
        assert rc == 0, err

    def test_no_op_outside_readme_required_trees(self, engineering_ops_project, run_hook):
        # index.md is a top-level allowed file, not under a readmeRequired pattern
        rc, _, err = run_hook("readme-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / ".memex" / "index.md")},
        })
        assert rc == 0


class TestDocRequired:
    def _config_with_mapping(self, project):
        """Add a code-to-doc mapping so doc-required has something to enforce."""
        cfg_path = project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["codeToDocMapping"] = [{
            "codePattern": "src/features/*/",
            "requiresDoc": "platform/features/{1}/README.md",
            "severity": "warn-then-block",
            "stateKey": "feature-doc",
        }]
        cfg_path.write_text(json.dumps(cfg))

    def test_warns_on_first_offence(self, engineering_ops_project, run_hook):
        self._config_with_mapping(engineering_ops_project)
        rc, _, err = run_hook("doc-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / "src" / "features" / "auth" / "index.ts")},
        })
        assert rc == 0
        assert "WARNING" in err
        assert "auth" in err

    def test_blocks_on_second_offence(self, engineering_ops_project, run_hook):
        self._config_with_mapping(engineering_ops_project)
        # First offence — warn
        run_hook("doc-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / "src" / "features" / "auth" / "a.ts")},
        })
        # Second offence — block
        rc, _, err = run_hook("doc-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / "src" / "features" / "auth" / "b.ts")},
        })
        assert rc == 2
        assert "BLOCKED" in err

    def test_allows_when_doc_exists(self, engineering_ops_project, run_hook):
        self._config_with_mapping(engineering_ops_project)
        doc = engineering_ops_project / ".memex" / "platform" / "features" / "auth" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("---\ntitle: Auth\n---\n")
        rc, _, err = run_hook("doc-required.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(engineering_ops_project / "src" / "features" / "auth" / "index.ts")},
        })
        assert rc == 0, err
        assert "WARNING" not in err


class TestIngestDocLink:
    def _config_with_block_mapping(self, project):
        cfg_path = project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["codeToDocMapping"] = [{
            "codePattern": "db/migrations/*.sql",
            "requiresDoc": "ANY .md containing the slug OR `-- Doc: .memex/<path>.md`",
            "severity": "block",
        }]
        cfg_path.write_text(json.dumps(cfg))

    def test_blocks_when_no_link(self, engineering_ops_project, run_hook):
        self._config_with_block_mapping(engineering_ops_project)
        migration = engineering_ops_project / "db" / "migrations" / "20260423_add_users.sql"
        rc, _, err = run_hook("ingest-doc-link.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(migration), "content": "CREATE TABLE users (id INT);"},
        })
        assert rc == 2
        assert "has no linked doc" in err

    def test_allows_with_header_comment(self, engineering_ops_project, run_hook):
        self._config_with_block_mapping(engineering_ops_project)
        migration = engineering_ops_project / "db" / "migrations" / "20260423_add_users.sql"
        rc, _, err = run_hook("ingest-doc-link.py", {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(migration),
                "content": "-- Doc: .memex/platform/systems/users/README.md\nCREATE TABLE users (id INT);",
            },
        })
        assert rc == 0, err

    def test_allows_when_referenced_in_wiki(self, engineering_ops_project, run_hook):
        self._config_with_block_mapping(engineering_ops_project)
        # Create a wiki page that mentions the slug
        doc = engineering_ops_project / ".memex" / "platform" / "systems" / "users" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("---\ntitle: Users\n---\n\nSee migration `20260423_add_users.sql` or slug `add_users`.")
        migration = engineering_ops_project / "db" / "migrations" / "20260423_add_users.sql"
        rc, _, err = run_hook("ingest-doc-link.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(migration), "content": "CREATE TABLE users (id INT);"},
        })
        assert rc == 0, err


class TestFrontmatterPrecheck:
    def test_warns_when_existing_frontmatter_broken(self, engineering_ops_project, run_hook):
        readme = engineering_ops_project / ".memex" / "entities" / "sample" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text("---\ntitle: Sample\n---\n")  # missing required fields
        rc, _, err = run_hook("frontmatter-precheck.py", {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(readme)},
        })
        # Precheck is non-blocking
        assert rc == 0
        assert "WARNING" in err

    def test_silent_on_valid_frontmatter(self, engineering_ops_project, run_hook):
        readme = engineering_ops_project / ".memex" / "entities" / "sample" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text(
            "---\ntitle: Sample\nslug: sample\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n"
        )
        rc, _, err = run_hook("frontmatter-precheck.py", {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(readme)},
        })
        assert rc == 0
        assert "WARNING" not in err

    def test_only_runs_on_edit_not_write(self, engineering_ops_project, run_hook):
        readme = engineering_ops_project / ".memex" / "entities" / "sample" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text("---\ntitle: Bad\n---\n")
        # Write (not Edit) — precheck should be silent
        rc, _, err = run_hook("frontmatter-precheck.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(readme)},
        })
        assert rc == 0
        assert "WARNING" not in err
