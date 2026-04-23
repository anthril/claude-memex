"""Tests for scripts/migrate_from_operations.py.

Scaffolds a Lumioh-shaped `.operations/` tree in a tmp project and verifies
the migration produces the expected `.memex/` tree + `memex.config.json`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "migrate_from_operations.py"


def make_lumioh_shaped_tree(project_root: Path) -> None:
    """Create a minimal Lumioh-shaped `.operations/` tree for testing."""
    ops = project_root / ".operations"
    (ops / ".rules").mkdir(parents=True)
    (ops / "entities" / "user").mkdir(parents=True)
    (ops / "platform" / "features" / "auth").mkdir(parents=True)
    (ops / "platform" / "systems" / "db").mkdir(parents=True)

    (ops / "AGENTS.md").write_text(
        "---\ntitle: Lumioh Agent Contract\nslug: agents\ntype: rule\n"
        "status: active\nowner: team\ncreated: 2024-01-01\nupdated: 2024-01-01\n---\n\n"
        "Follow .operations/ rules strictly."
    )
    (ops / "README.md").write_text(
        "---\ntitle: Ops\nslug: ops-root\ntype: rule\nstatus: active\nowner: team\n"
        "created: 2024-01-01\nupdated: 2024-01-01\n---\n\nFolder map.\n"
    )
    (ops / "log.md").write_text("# Log\n\n## [2024-01-01] init | lumioh\n")
    (ops / "index.md").write_text("# Index\n")
    (ops / "entities" / "user" / "README.md").write_text(
        "---\ntitle: User\nslug: user\ntype: entity\nstatus: active\nowner: team\n"
        "created: 2024-01-01\nupdated: 2024-01-01\n---\n\nUser entity.\n"
    )
    (ops / "platform" / "features" / "auth" / "README.md").write_text(
        "---\ntitle: Auth\nslug: auth\ntype: feature\nstatus: active\nowner: team\n"
        "created: 2024-01-01\nupdated: 2024-01-01\n---\n\nAuth feature.\n"
    )

    # A few Supabase-shaped paths to trigger the code-to-doc mapping inference
    (project_root / "supabase" / "functions" / "send-email").mkdir(parents=True)
    (project_root / "supabase" / "functions" / "send-email" / "index.ts").write_text("// edge fn\n")
    (project_root / "supabase" / "migrations").mkdir(parents=True)
    (project_root / "supabase" / "migrations" / "20240101000000_init.sql").write_text("-- init\n")

    # An in-tree reference that should be flagged for rewrite
    (project_root / "CLAUDE.md").write_text(
        "See .operations/AGENTS.md for the agent contract.\n"
    )


def run_migrate(project_root: Path, dry_run: bool) -> dict:
    cmd = [sys.executable, str(SCRIPT), "--project-root", str(project_root)]
    if dry_run:
        cmd.append("--dry-run")
    p = subprocess.run(
        cmd,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL,  # Windows/py3.14/pytest-capture compat
    )
    assert p.returncode == 0, f"migration failed: rc={p.returncode}, stderr={p.stderr}"
    return json.loads(p.stdout)


class TestDryRun:
    def test_plan_detects_valid_tree(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        result = run_migrate(tmp_path, dry_run=True)
        assert result["ok"] is True
        assert result["executed"] is False
        assert not (tmp_path / ".memex").exists(), "dry-run must not move anything"
        assert (tmp_path / ".operations").exists()

    def test_plan_lists_move_action(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        result = run_migrate(tmp_path, dry_run=True)
        actions = [a["kind"] for a in result["actions"]]
        assert "move" in actions
        assert "create" in actions  # memex.config.json
        assert "log-append" in actions

    def test_plan_infers_code_to_doc_mappings(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        result = run_migrate(tmp_path, dry_run=True)
        create = [a for a in result["actions"] if a["kind"] == "create"][0]
        # The preview shows the mapping count — should be 2 (edge fns + migrations)
        assert create["preview"]["codeToDocMapping_count"] == 2

    def test_plan_flags_reference_hits(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        result = run_migrate(tmp_path, dry_run=True)
        # Our fixture puts `.operations/` into CLAUDE.md — must be surfaced
        assert "reference_hits" in result
        hits = result["reference_hits"]
        # The in-tree .operations/**/*.md files also contain the string but those will be
        # renamed atomically; the CLAUDE.md reference is the one we care about
        paths = [h["path"] for h in hits]
        assert "CLAUDE.md" in paths


class TestExecute:
    def test_move_happens(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        result = run_migrate(tmp_path, dry_run=False)
        assert result["ok"] is True
        assert result["executed"] is True
        assert not (tmp_path / ".operations").exists()
        assert (tmp_path / ".memex").exists()
        # Content preserved
        assert (tmp_path / ".memex" / "AGENTS.md").exists()
        assert (tmp_path / ".memex" / "entities" / "user" / "README.md").exists()

    def test_config_written(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        run_migrate(tmp_path, dry_run=False)
        cfg = json.loads((tmp_path / "memex.config.json").read_text())
        assert cfg["profile"] == "engineering-ops"
        assert cfg["root"] == ".memex"
        assert "entities" in cfg["allowedTopLevel"]
        # Inferred mappings from Supabase presence
        mappings = cfg["codeToDocMapping"]
        assert any(m["codePattern"] == "supabase/functions/*/" for m in mappings)
        assert any(m["codePattern"] == "supabase/migrations/*.sql" for m in mappings)

    def test_log_gets_migrate_entry(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        run_migrate(tmp_path, dry_run=False)
        log_content = (tmp_path / ".memex" / "log.md").read_text(encoding="utf-8")
        assert "migrate | .operations/ -> .memex/" in log_content

    def test_refuses_when_memex_exists(self, tmp_path):
        make_lumioh_shaped_tree(tmp_path)
        (tmp_path / ".memex").mkdir()
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(tmp_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL,
        )
        assert p.returncode == 1
        result = json.loads(p.stdout)
        assert result["ok"] is False
        assert any("already exists" in e for e in result["errors"])

    def test_refuses_when_operations_missing(self, tmp_path):
        # Empty project — no .operations/
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(tmp_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL,
        )
        assert p.returncode == 1
        result = json.loads(p.stdout)
        assert result["ok"] is False
        assert any("No .operations/" in e for e in result["errors"])


class TestMigratedTreeWorks:
    """After migration, the new `.memex/` tree should pass Memex hooks."""

    def test_path_guard_accepts_migrated_tree(self, tmp_path, run_hook):
        make_lumioh_shaped_tree(tmp_path)
        run_migrate(tmp_path, dry_run=False)

        # A write under the migrated entities/ folder should be accepted
        target = tmp_path / ".memex" / "entities" / "new-entity" / "README.md"
        rc, _, err = run_hook("path-guard.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
        })
        assert rc == 0, f"path-guard rejected migrated tree target: {err}"

    def test_frontmatter_check_passes_on_migrated_files(self, tmp_path, run_hook):
        make_lumioh_shaped_tree(tmp_path)
        run_migrate(tmp_path, dry_run=False)

        migrated_readme = tmp_path / ".memex" / "AGENTS.md"
        rc, _, err = run_hook("frontmatter-check.py", {
            "tool_name": "Write",
            "tool_input": {"file_path": str(migrated_readme)},
        })
        assert rc == 0, f"migrated AGENTS.md failed frontmatter-check: {err}"
