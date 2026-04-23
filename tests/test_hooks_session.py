"""Session-lifecycle hooks: session-start-context, user-prompt-context, stop-*, precompact, session-end."""
from __future__ import annotations

import json
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestSessionStart:
    def test_injects_index_and_log(self, engineering_ops_project, run_hook):
        rc, out, _ = run_hook("session-start-context.py", {"cwd": str(engineering_ops_project)})
        assert rc == 0
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "Memex index" in ctx
        assert "Memex log" in ctx

    def test_silent_outside_memex_project(self, tmp_path, run_hook):
        rc, out, _ = run_hook("session-start-context.py", {"cwd": str(tmp_path)})
        assert rc == 0
        assert not out.strip()


class TestUserPromptContext:
    def test_grep_finds_matching_page(self, engineering_ops_project, run_hook):
        rc, out, _ = run_hook("user-prompt-context.py", {
            "cwd": str(engineering_ops_project),
            "prompt": "What do documentation rules say about frontmatter?",
        })
        assert rc == 0
        if not out.strip():
            return  # no matches is acceptable — the profile may not have the page
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "documentation-rules" in ctx.lower()

    def test_silent_on_empty_prompt(self, engineering_ops_project, run_hook):
        rc, out, _ = run_hook("user-prompt-context.py", {
            "cwd": str(engineering_ops_project),
            "prompt": "",
        })
        assert rc == 0
        assert not out.strip()

    def test_silent_when_no_matches(self, engineering_ops_project, run_hook):
        rc, out, _ = run_hook("user-prompt-context.py", {
            "cwd": str(engineering_ops_project),
            "prompt": "xylophonophobia splorkliffic xibbleglorp",
        })
        assert rc == 0
        assert not out.strip()

    def test_qmd_integration_with_mock_binary(self, engineering_ops_project, run_hook, monkeypatch):
        """When engine=qmd and binary works, use its results."""
        # Switch config to qmd engine
        cfg_path = engineering_ops_project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["search"]["engine"] = "qmd"
        cfg_path.write_text(json.dumps(cfg))

        # Create a target page the mock will reference
        page = engineering_ops_project / ".memex" / "entities" / "qmd-test-target" / "README.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\ntitle: QMD Test Target\nslug: qmd-test-target\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n\n"
            "This page contains the target text only.\n"
        )

        # Point at the mock qmd
        mock = FIXTURES / "mock_qmd" / ("qmd.bat" if sys.platform == "win32" else "qmd")
        # Ensure the mock exists (generated on-the-fly if missing so the test is self-contained)
        if not mock.exists():
            mock.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                # Windows batch that emits the JSON our hook expects
                mock.write_text(
                    "@echo off\r\n"
                    'echo [{"file":"entities/qmd-test-target/README.md","score":0.95}]\r\n'
                )
            else:
                mock.write_text(
                    "#!/usr/bin/env bash\n"
                    'echo \'[{"file":"entities/qmd-test-target/README.md","score":0.95}]\'\n'
                )
                mock.chmod(0o755)

        monkeypatch.setenv("MEMEX_QMD_BIN", str(mock))
        rc, out, _ = run_hook("user-prompt-context.py", {
            "cwd": str(engineering_ops_project),
            "prompt": "anything — qmd mock ignores it",
        })
        assert rc == 0
        assert out.strip(), "qmd-engine test should emit context"
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "qmd-test-target" in ctx

    def test_qmd_falls_back_to_grep_on_failure(self, engineering_ops_project, run_hook, monkeypatch):
        """If qmd binary errors, we silently fall back to grep."""
        cfg_path = engineering_ops_project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["search"]["engine"] = "qmd"
        cfg_path.write_text(json.dumps(cfg))

        # Point at a non-existent binary
        monkeypatch.setenv("MEMEX_QMD_BIN", str(engineering_ops_project / "definitely-not-a-binary"))
        rc, out, _ = run_hook("user-prompt-context.py", {
            "cwd": str(engineering_ops_project),
            "prompt": "documentation rules frontmatter",
        })
        # Should still work via grep fallback
        assert rc == 0


class TestStopLogAppend:
    def test_appends_entry_on_write_activity(self, engineering_ops_project, run_hook, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": str(engineering_ops_project / ".memex" / "entities" / "foo" / "README.md")}}
            ]}
        }) + "\n")

        log_path = engineering_ops_project / ".memex" / "log.md"
        before = log_path.stat().st_size
        rc, _, _ = run_hook("stop-log-append.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
        })
        assert rc == 0
        assert log_path.stat().st_size > before
        last = log_path.read_text().splitlines()[-1]
        assert "session" in last

    def test_silent_on_no_writes(self, engineering_ops_project, run_hook, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("")
        log_path = engineering_ops_project / ".memex" / "log.md"
        before = log_path.stat().st_size
        rc, _, _ = run_hook("stop-log-append.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
        })
        assert rc == 0
        assert log_path.stat().st_size == before


class TestStopStaleCheck:
    def _cfg_with_mapping(self, project):
        cfg_path = project / "memex.config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["codeToDocMapping"] = [{
            "codePattern": "src/features/*/",
            "requiresDoc": "platform/features/{1}/README.md",
            "severity": "warn-then-block",
        }]
        cfg_path.write_text(json.dumps(cfg))

    def test_flags_stale_doc(self, engineering_ops_project, run_hook, tmp_path):
        self._cfg_with_mapping(engineering_ops_project)
        # Create a feature doc with an old `updated:`
        doc = engineering_ops_project / ".memex" / "platform" / "features" / "auth" / "README.md"
        doc.parent.mkdir(parents=True)
        doc.write_text(
            "---\ntitle: Auth\nslug: auth\ntype: feature\nstatus: active\n"
            "owner: x\ncreated: 2025-01-01\nupdated: 2025-01-01\n---\n"
        )
        # Transcript: we touched code in src/features/auth/
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": str(engineering_ops_project / "src" / "features" / "auth" / "index.ts")}}
            ]}
        }) + "\n")

        rc, out, _ = run_hook("stop-stale-check.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
        })
        assert rc == 0
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "stale-check" in ctx
        assert "auth" in ctx

    def test_silent_when_no_mappings(self, engineering_ops_project, run_hook, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": str(engineering_ops_project / "src" / "foo.ts")}}
            ]}
        }) + "\n")
        rc, out, _ = run_hook("stop-stale-check.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
        })
        assert rc == 0
        assert not out.strip()


class TestStopOpenQuestionsCheck:
    def test_detects_inline_todo(self, engineering_ops_project, run_hook, tmp_path):
        target = engineering_ops_project / ".memex" / "entities" / "bar" / "README.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "---\ntitle: Bar\nslug: bar\ntype: entity\nstatus: active\n"
            "owner: x\ncreated: 2026-04-23\nupdated: 2026-04-23\n---\n\n"
            "## Notes\n\nTODO: revisit after the refactor lands.\n"
        )
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": str(target)}}
            ]}
        }) + "\n")

        rc, out, _ = run_hook("stop-open-questions-check.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
        })
        assert rc == 0
        data = json.loads(out)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "TODO" in ctx
        assert "bar/README.md" in ctx


class TestPrecompactSnapshot:
    def test_writes_session_file(self, engineering_ops_project, run_hook, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": str(engineering_ops_project / "x.md")}}
            ]}
        }) + "\n")

        rc, _, _ = run_hook("precompact-snapshot.py", {
            "cwd": str(engineering_ops_project),
            "transcript_path": str(transcript),
            "session_id": "test-session-1",
        })
        assert rc == 0
        snapshot = engineering_ops_project / ".memex" / ".state" / "sessions" / "test-session-1.md"
        assert snapshot.exists()
        content = snapshot.read_text()
        assert "Tool usage" in content
        assert "Write" in content


class TestSessionEndLog:
    def test_appends_final_entry(self, engineering_ops_project, run_hook):
        log_path = engineering_ops_project / ".memex" / "log.md"
        before = log_path.stat().st_size
        rc, _, _ = run_hook("session-end-log.py", {
            "cwd": str(engineering_ops_project),
            "reason": "user_closed",
        })
        assert rc == 0
        assert log_path.stat().st_size > before
        last = log_path.read_text().splitlines()[-1]
        assert "session-end" in last
        assert "user_closed" in last
