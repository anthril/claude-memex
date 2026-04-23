"""PostToolUse hooks: frontmatter-check, index-update."""
from __future__ import annotations

import json


class TestFrontmatterCheck:
    def test_blocks_missing_required_fields(self, engineering_ops_project, run_hook):
        target = engineering_ops_project / ".memex" / "entities" / "bad" / "README.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\ntitle: Bad\n---\nbody")
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 2
        assert "missing required field" in err

    def test_blocks_invalid_enum(self, engineering_ops_project, run_hook):
        target = engineering_ops_project / ".memex" / "entities" / "bad" / "README.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "---\ntitle: Bad\nslug: bad\ntype: nonsense\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n"
        )
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 2
        assert "invalid value" in err

    def test_allows_valid_frontmatter(self, engineering_ops_project, run_hook):
        target = engineering_ops_project / ".memex" / "entities" / "good" / "README.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "---\ntitle: Good\nslug: good\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n\nbody"
        )
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, err

    def test_skips_files_outside_applies_to(self, engineering_ops_project, run_hook):
        # A raw/article markdown doesn't match **/README.md — should skip
        target = engineering_ops_project / ".memex" / "entities" / "foo" / "notes.md"
        # notes.md is not README.md, so frontmatter-check should skip it regardless of content.
        # But path-guard would have blocked it anyway — for this test we bypass by writing
        # the file directly to disk then invoking frontmatter-check.
        target.parent.mkdir(parents=True)
        target.write_text("no frontmatter here")
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0


class TestIndexUpdate:
    def test_nudges_when_page_not_indexed(self, engineering_ops_project, run_hook):
        page = engineering_ops_project / ".memex" / "entities" / "my-ent" / "README.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\ntitle: My Entity\nslug: my-ent\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n\nbody"
        )
        rc, out, _ = run_hook("index-update.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(page)},
        })
        assert rc == 0
        assert out.strip(), "expected additionalContext output"
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "entities/my-ent/README.md" in ctx
        # section-aware: should suggest "Entities"
        assert "Entities" in ctx

    def test_silent_when_page_already_in_index(self, engineering_ops_project, run_hook):
        page = engineering_ops_project / ".memex" / "entities" / "my-ent" / "README.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\ntitle: My Entity\nslug: my-ent\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n"
        )
        # Update index to reference this page
        index = engineering_ops_project / ".memex" / "index.md"
        index.write_text(
            "# Index\n\n## Entities\n- [My Entity](entities/my-ent/README.md)\n"
        )
        rc, out, _ = run_hook("index-update.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(page)},
        })
        assert rc == 0
        assert not out.strip(), f"should be silent when already indexed, got: {out}"

    def test_silent_for_structural_files(self, engineering_ops_project, run_hook):
        # index.md itself shouldn't trigger the index-update hook
        index = engineering_ops_project / ".memex" / "index.md"
        rc, out, _ = run_hook("index-update.py", {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(index)},
        })
        assert rc == 0
        assert not out.strip()

    def test_silent_for_open_questions(self, engineering_ops_project, run_hook):
        q = engineering_ops_project / ".memex" / ".open-questions" / "my-q.md"
        q.write_text("---\ntitle: Q\ntype: open-question\n---\n")
        rc, out, _ = run_hook("index-update.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(q)},
        })
        # .open-questions/ is excluded from nudges
        assert rc == 0
        assert not out.strip()

    def test_suggests_section_by_frontmatter_type(self, engineering_ops_project, run_hook):
        # Put a page in a folder that doesn't directly name-match,
        # but set `type:` explicitly to one that does.
        page = engineering_ops_project / ".memex" / "workflows" / "checkout" / "README.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\ntitle: Checkout\nslug: checkout\ntype: workflow\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n"
        )
        rc, out, _ = run_hook("index-update.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(page)},
        })
        assert rc == 0
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "Workflows" in ctx
