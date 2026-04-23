# Changelog

All notable changes to `claude-memex` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org/).

## [Unreleased]

### Added

- **Unicode wiki slugs.** `path-guard` now accepts lowercase / caseless letters from any Unicode script by default — Japanese, Chinese, Korean, Greek, Cyrillic, Arabic, Hebrew, Thai (with combining marks), etc. Tracked via `naming.asciiOnly` in `memex.config.json` (default `false`). Set `true` to restrict to ASCII `[a-z0-9]`. Extensions stay ASCII for cross-platform file-system portability regardless of the flag.
- **Plugin auto-update notifications.** New `hooks/scripts/update-check.py` SessionStart hook optionally polls GitHub once every 24h for a newer release and surfaces a notice as `additionalContext`. **Off by default** — opt in via `hookEvents.sessionStart.updateCheck: true`. Cached at `.memex/.state/update-check.json`. Corporate / offline environments can set `updateCheckUrl` to a mirror. `MEMEX_UPDATE_CHECK_JSON` env override enables fixture-based testing. Full SemVer-aware version comparison (release beats same-core prerelease; prerelease compare lexicographic).
- **Shared templates.** `templates/shared/agents.md.tmpl` and `templates/shared/claude.md.tmpl` — previously missing from the plan §4 layout.
- **Migration script.** `scripts/migrate_from_operations.py` — the `/memex:migrate-from-operations` slash command now shells out to a tested Python script that: detects a Lumioh-shaped `.operations/` tree, infers code-to-doc mappings from the target project's structure (Next.js features, Supabase functions, Supabase migrations), proposes a plan, and executes the rename + config extraction. `--dry-run` previews without touching anything. Refuses to overwrite existing `.memex/`.
- **Worked ingest example.** `examples/research-wiki-demo/` is now a **fully-realised** post-ingest research wiki: one source in `raw/articles/`, its summary, extracted entity + two concept pages, surfaced open question, updated index and log. `WALKTHROUGH.md` tells the full story. Verified by `tests/test_demo_ingest.py` (35 tests covering structure, frontmatter, cross-references, index coverage, log entries, and hook compatibility).

### Fixed

- `hooks/scripts/stop-log-append.py:8` — stale `scribe-ingestor` reference in docstring replaced with `memex-ingestor`.
- `hooks/scripts/user-prompt-context.py:55` — dead `ops_root_norm` variable (previously audited as a SUGGESTION) is no longer present.

### Closes gaps flagged in v0.1.0-alpha.1 audit

- **Ingest polish**: end-to-end demo in `examples/research-wiki-demo/` is verified by construction. No longer a "documented only" contract.
- **Non-English wiki support**: Unicode kebab slugs work across 11+ tested scripts including Thai with combining marks.
- **Plugin auto-update notifications**: implemented and tested, off by default.

### Changed

- **Removed `llm-wiki.md` from the repo root.** Karpathy's gist is now linked, not redistributed — every reference points at https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f. Updated across README, CREDITS, docs/concepts, all five profile AGENTS.md files, the shared template, the demo AGENTS, and the attribution tests.
- **Refactored `glob_to_regex` + `substitute` into `hooks/scripts/_lib/patterns.py`.** Previously copy-pasted across `doc-required.py`, `ingest-doc-link.py`, and `stop-stale-check.py`. One copy, tested in `test_lib.py`.
- **Lint + type check now pass cleanly.** `ruff check hooks/ tests/ scripts/` — 0 findings. `mypy hooks/` — 0 errors across 23 files.

### Added (tooling + governance)

- **`pyproject.toml` dev stack.** `[project.optional-dependencies.dev]` adds pytest, ruff, mypy. `[tool.ruff]` and `[tool.mypy]` configured with sensible defaults.
- **CI workflow.** `.github/workflows/ci.yml` runs pytest + ruff + mypy across Ubuntu / macOS / Windows on Python 3.10 and 3.12 for every push and PR.
- **Governance files.**
  - `SECURITY.md` — threat model, reporting channels, SLAs
  - `CONTRIBUTING.md` — dev setup, coding conventions, PR checklist
  - `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
  - `.github/CODEOWNERS` — review routing
  - `.github/PULL_REQUEST_TEMPLATE.md` + `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md`
- **`.gitignore` secret patterns.** `.env`, `.env.*.local`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials.json`, `secrets.json`, `.aws/`, `.azure/`, `.gcp/` now excluded by default (safety net for forks).

### Test coverage

Now **227 tests** in `tests/` (up from 111 in alpha.1, +9 new for the `_lib/patterns` refactor):

- `test_unicode_paths.py` — 41 tests (Unicode kebab + ASCII-only mode + hook integration)
- `test_migration.py` — 11 tests (dry-run, execute, config inference, refusal conditions, post-migration hook compat)
- `test_demo_ingest.py` — 35 tests (contract verification of the worked example)
- `test_update_check.py` — 20 tests (SemVer compare + fixture-based hook behaviour)
- New `TestPatterns` class in `test_lib.py` — 9 tests for `glob_to_regex` + `substitute`
- All 111 prior tests still pass

---

## [0.1.0-alpha.1] — 2026-04-23

Initial alpha. Full enforcement + session-lifecycle + wiki-operations loop.

### Added

**Plugin core**
- Plugin manifest (`.claude-plugin/plugin.json`)
- Hook wiring (`hooks/hooks.json`) covering `SessionStart`, `UserPromptSubmit`, `PreToolUse` (Write|Edit), `PostToolUse` (Write|Edit), `Stop`, `PreCompact`, `SessionEnd`
- Shared hook helpers in `hooks/scripts/_lib/` (`config.py`, `paths.py`, `frontmatter.py`, `state.py`)
- UTF-8 stderr reconfiguration so hook messages surface correctly on Windows consoles

**Enforcement hooks (Phase 1)**
- `path-guard.py` — kebab-case, dated-folder format, top-level allowlist
- `readme-required.py` — README-must-exist-first enforcement for slug folders
- `frontmatter-check.py` — required fields + enum validation (PostToolUse)
- `frontmatter-precheck.py` — non-blocking pre-Edit validation (PreToolUse)
- `doc-required.py` — code-to-doc mapping with warn-then-block session state
- `ingest-doc-link.py` — migration-like artifact → doc link requirement
- `index-update.py` — non-blocking nudge when new pages aren't indexed

**Session-lifecycle hooks (Phase 2)**
- `session-start-context.py` — injects `index.md` head + recent `log.md` entries
- `user-prompt-context.py` — grep-based (fallback to `qmd`) wiki retrieval for user prompts
- `stop-log-append.py` — appends chronological log entries
- `stop-stale-check.py` — flags pages referencing code touched without `updated:` bump
- `stop-open-questions-check.py` — detects inline TODO/TBD in session writes
- `precompact-snapshot.py` — writes session snapshot to `.memex/.state/sessions/`
- `session-end-log.py` — final log entry on session termination

**Skills (Phase 3)**
- `ingest-source` — 10-step ingest flow for raw source → wiki pages
- `doc-query` — search + synthesise cited answers; offer to file back
- `wiki-lint` — orphan / contradiction / stale / missing-cross-ref health check
- `open-questions-triage` — age-bucketed triage with resolution proposals
- `doc-refactor` — split / merge / rename with automatic cross-reference updates

**Subagents**
- `memex-ingestor` — isolated single-source ingest (worktree)
- `memex-linter` — isolated wiki-lint pass (worktree)
- `memex-planner` — pre-task wiki read, returns a plan

**Commands**
- `/memex:init` — scaffold `.memex/` + `memex.config.json` + `CLAUDE.md`
- `/memex:ingest` — ingest a source
- `/memex:query` — ask the wiki
- `/memex:lint` — health-check
- `/memex:log` — view / edit the log
- `/memex:open-q` — file a new open question
- `/memex:promote` — promote a transient doc to a permanent wiki page
- `/memex:graph` — emit the link graph (mermaid / dot / json)
- `/memex:migrate-from-operations` — Lumioh-style `.operations/` → `.memex/` migration helper

**Profiles**
- `engineering-ops` — SaaS / product codebases; entities, features, systems, workers, workflows, agents
- `research-wiki` — multi-source research; closest to Karpathy's `llm-wiki.md`; raw/ + wiki/entities/concepts/summaries/analyses/syntheses
- `book-companion` — reading a long book; characters, places, themes, plot-threads, timeline
- `personal-journal` — private self-tracking; topics, goals, reflections
- `generic` — minimal starting point

**Schema**
- `schemas/memex.config.schema.json` — JSON Schema for `memex.config.json`

**Docs**
- `README.md` — project overview with Karpathy attribution
- `CREDITS.md` — full prior-art attribution
- `docs/concepts.md` — three-layer model, three operations, prior art
- `docs/hook-catalog.md` — every hook, when it fires, what it enforces
- `docs/profile-authoring.md` — how to write a new profile
- `docs/cookbook.md` — practical recipes for customisation
- `docs/README.md` — command + skill reference

**Examples**
- `examples/engineering-ops-demo/` — placeholder
- `examples/research-wiki-demo/` — placeholder + walkthrough of expected ingest result

### Attribution

Karpathy's [`llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026) is the conceptual origin. The name nods to Vannevar Bush's 1945 Memex essay. Full attribution in [CREDITS.md](CREDITS.md).

### Known gaps

- `/memex:ingest` can be invoked but the end-to-end skill is documented; real-world ingest polish comes from the v0.1.0 final dogfood.

### Closed during alpha

- **Test harness.** `tests/` with 111 pytest tests covering every hook, every profile, every `_lib/*` helper, and attribution integrity. Runs hermetically — no network, no shared state. `pytest tests/ -v`.
- **`index-update.py` is now section-aware.** New `_lib/index_parse.py` parses index sections, extracts both markdown and wikilinks, and suggests the correct section via frontmatter `type:` or folder name. Replaces the previous crude string match.
- **`qmd` integration hardened.** Now uses the real `qmd query --json -n <n>` interface; robust JSON parsing handles both list and object forms; graceful grep fallback on any failure; `MEMEX_QMD_BIN` env override enables testing against a mock. Verified via `test_hooks_session.py::TestUserPromptContext::test_qmd_integration_with_mock_binary`.

### Not yet supported

- Non-English wikis (the naming regex assumes ASCII kebab-case; Unicode slugs won't pass the path-guard)
- MCP server integration (reading / writing the wiki from non-Claude clients)
- Plugin auto-update notifications
