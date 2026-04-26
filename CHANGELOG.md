# Changelog

All notable changes to `claude-memex` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0-alpha.8] — 2026-04-27

### Added

- **Section landing pages now render a collapsible folder tree** instead of a flat page list. Pages group by their folder structure with `<details open>` elements you can click to collapse, count badges per folder, and folder-index pages (`<folder>/index.md`, `<folder>/README.md`) attached to their parent folder so the folder summary itself navigates to the landing page. Within each directory, folders sort first then leaves; both alphabetical. Built via a new `build_section_tree` in `memex_docsite/sections.py` that returns a recursive `SectionTreeNode` consumed by `templates/sections/section.html`.

### Tests

- 3 new sections tests (folder grouping, folder-index attachment, sort order) and 1 server-route test verifying the section detail page renders the new tree markup.

## [0.1.0-alpha.7] — 2026-04-27

### Fixed

- **Pages without frontmatter still showed duplicate H1s.** The previous duplicate-title strip only matched when `frontmatter.title` was set; pages that relied on the body's first H1 to define their title still rendered it twice (once as the chrome `<h1>{{ page.title }}</h1>`, once in the body). Stripping is now unconditional — the body's leading H1 is always removed and its text becomes the title fallback when frontmatter has none.
- **Folder-index pages reported false-positive broken links to siblings.** When a URL like `/foo/bar/` was served from `<wiki>/foo/bar/index.md`, the page route was passing the URL slug (`foo/bar`) to the renderer rather than the file's canonical slug (`foo/bar/index`). The renderer's `source_dir = source_slug.rsplit("/", 1)[0]` then resolved to `foo` instead of `foo/bar`, so every relative link in `index.md` was searched one folder too high. Now passes the canonical file slug.
- **Wikilinks to sibling pages were marked broken.** `[[criterion-1-local-learning]]` from a page at `architecture/.../stage-1-experiments/index.md` only tried the absolute root slug. Now cascades: absolute → sibling-relative → ancestor walk, matching the Obsidian-style convention most users expect. Absolute matches still win when both exist (preserves the existing "every slug is unique" contract).

### Tests

- Updated `test_renderer_basic_round_trip` for the unconditional-strip behaviour. New tests for: H1 strip with differing frontmatter title; H1 promotion to title when no frontmatter; sibling wikilink fallback; ancestor-walk wikilink fallback; absolute wikilink precedence; folder-index relative-link route regression.

## [0.1.0-alpha.6] — 2026-04-27

### Fixed

- **Links to non-markdown asset files (`.json`, `.svg`, `.pdf`, `.png`, `.csv`, etc.) were marked broken even when the file existed.** The renderer's relative-link resolver only matched markdown targets — every link to a JSON schema, SVG diagram, or PDF report under the wiki root showed up as a broken link with a 404 if clicked. The resolver now does a two-pass match (markdown first, asset fallback), and the page route serves the literal file via `FileResponse` with a guessed content-type. Aurora went from **95 → 2 broken links** after this single fix; the remaining 2 are intentional `<YYYY-MM-DDTHH:MM:SSZ>` template placeholder markers in a `templates/` file.
- **Folder links (`decisions/`, `data/`) failed when the folder used `README.md` instead of `index.md`.** `slug_to_path` only checked the README fallback at the wiki root, not for subfolders. Now any folder slug also tries `<slug>/README.md` — matches the convention of every github-rooted markdown repo.
- **Links to folders that the live server *would* render via the auto-generated folder index were marked broken anyway.** The resolver now accepts directory targets that exist under the wiki root, since `_folder_response` will serve them regardless of whether they have a README/index.

### Tests

- 4 new renderer tests (asset resolution / folder fallback / no-README directories / sanity preserves real broken links) and 2 server-route tests (asset serving + missing-asset 404).

## [0.1.0-alpha.5] — 2026-04-26

### Fixed

- **Duplicate page titles.** Pages whose markdown body started with a `# Title` matching the frontmatter `title:` rendered two H1s — the chrome-rendered `<h1>{{ page.title }}</h1>` plus the body's own. The renderer now strips the body's leading H1 when its plain text matches the frontmatter title (case-insensitive). H1s that differ from the title are left alone, and pages without frontmatter title keep their body H1 as before.

### Added

- **Sidebar sections grouped by origin.** The Sections nav now splits into three labelled groups: **Wiki** (curated content — sections that map to a `frontmatter.enum.type` value), **Project** (authored content — sections matched only by folder convention), and an unlabelled **meta** group at the bottom for Recent Activity / Uncategorised. The grouping is automatic via a new `Section.kind` property; no config change required. Lets users at a glance see where Claude is meant to write versus where they author content directly.

### Tests

- 4 renderer tests (matching strip / case-insensitive / non-match preserved / no-frontmatter case) and 1 sections test (kind classification).

## [0.1.0-alpha.4] — 2026-04-26

### Fixed

- **Sections nav was empty whenever `docsite.contentRoot` was widened past `.memex/`.** Every wiki page's path then started with `.memex/...` so its `Node.is_hidden` flag was True; `build_sections` was unconditionally skipping hidden nodes, which dropped the entire wiki from the sections nav. The loop (and the recent-activity loop) now respect `cfg.show_hidden` instead — matching the graph builder's behaviour. Wikis using the default root are unaffected.

### Added

- **Folder-based section fallback.** When a node has no `frontmatter.type` (or its type isn't in any section's `type_values`), the page now lands in the first section whose `slug` or kebab'd label matches its first non-dot folder segment. Lets a page at `architecture/foo.md` land in an "Architecture" section without needing `type: architecture` on every file. Existing type-based assignment still wins where it applies.
- **Sidebar shortcut deduplication.** Sections whose slug duplicates a hardcoded sidebar shortcut (`open-questions`, `rule(s)`, `comments`, `graph`) are now hidden from the sections nav — they keep their `/sections/<slug>/` landing page but don't render in the sidebar a second time.

### Tests

- 3 new regression tests in `test_docsite_sections.py` (folder fallback, dot-segment skipping) and 1 in `test_docsite_routes_phase2.py` (sidebar shortcut suppression).

## [0.1.0-alpha.3] — 2026-04-26

### Fixed

- **Open-question + rule listing URLs 404'd when `docsite.contentRoot` was widened.** Aurora and other projects that set `contentRoot: "."` (so the docsite serves the whole repo, not just `.memex/`) had every entry in `/open-questions` and `/rules` link to a 404 — the listings built URLs relative to the canonical `memex_root` while the page handler routes against the wider `wiki_root`. Both helpers now use `wiki_root`, so URLs include the `.memex/` prefix when needed and resolve cleanly.

### Added

- **`memex-docsite serve --reload`** — re-imports the app on file changes (watches the project root + the installed `memex_docsite` package). Useful during development; production deployments should keep the default `serve` (no reload) for efficiency. Implemented via `make_app_from_env` factory + uvicorn's reload mode.

### Tests

- Two regression tests in `tests/test_docsite_routes_phase3.py` — one against `contentRoot: "."` (must route via `/.memex/...`) and a companion against the default root (must keep `/.open-questions/...` working).

## [0.1.0-alpha.2] — 2026-04-26

### Added

- **`research-project` profile** — for research/planning projects that will migrate into development (e.g. an architecture proposal with literature review, hypotheses, experiments, and planned systems). Superset of `research-wiki` with first-class `research/`, `architecture/`, `systems/`, `evaluation/` surfaces.
- **`profile-builder` skill + `/memex:init-profile` command** — interactive profile scaffolding for projects whose shape doesn't match any built-in profile. Surveys the project, interviews the user, generates a custom `memex.config.json` + `.memex/` tree. Worked example under `examples/custom-profile-demo/WALKTHROUGH.md`.
- **`research-wiki` raw classifications** — `raw/` tree expanded from `articles/papers/assets/` to also include `books/`, `transcripts/`, `videos/`, `interviews/`, `standards/`, `datasets/`, `notes/`.
- **`memex-docsite` — optional self-hosted browsable wiki.** Phase 1 markdown viewer with sidebar nav and dark mode; Phase 2 search + link graph; Phase 3 open-question and rule submissions; Phase 4 W3C-style inline annotations; Phase 5 page-level comments; Phase 6 Docker self-host image; Phase 7 polish (breadcrumbs, backlinks, ToC, mobile, keyboard). Stdlib hooks remain dependency-free; the docsite adds Starlette + Uvicorn + Jinja2 + Mistune + PyYAML behind the `[docsite]` extra. Install with `pip install -e ".[docsite]"`, then `memex-docsite serve` (or `/memex:docsite serve`). See [`docs/docsite.md`](docs/docsite.md).
- **Profile-driven sections nav in the docsite.** Sidebar surfaces a "Sections" group derived from `memex.config.json#/index.sections` and `frontmatter.enum.type`; `/sections/<type-slug>/` landing pages list every page of that type with coloured badges. The schema's `index.sections` accepts an array-of-objects form for many-to-one bridges (e.g. `engineering-ops` Planning ↔ `prd|rfc|decision`).
- **Inline `status: resolved` open questions display correctly.** Pages with `status: resolved` in frontmatter now appear in the docsite's Resolved bucket regardless of folder location, with a coloured badge and `resolved-on` date. Sort order: oldest pending first, most recently resolved first.
- **3D Obsidian-style link graph.** The `/graph` page replaces Mermaid with `3d-force-graph` + `force-graph` (vendored, MIT). 3D by default with hover labels and click-to-navigate; toggle 2D fallback for keyboard-friendly use. Includes node-size and link-distance controls. Exports JSON.
- **`/memex:docsite` slash command** — wraps `serve | build | check` so the docsite is reachable from inside Claude Code.
- **Browser-driven docsite writes append to `log.md`.** Open-question / rule / comment / annotation submissions made through the docsite UI now show up in the next session's SessionStart context just like Claude-driven edits.
- **Inline TODOs surface in `/open-questions`.** The `stop-open-questions-check.py` Stop hook persists findings to `.memex/.state/inline-todos.json`, which the docsite renders as an "Inline TODOs" banner so unpromoted markers are visible to readers.

### Changed

- **`engineering-ops` profile expanded** for real-world SaaS projects: adds `planning/{prds,rfcs,decisions}`, `platform/integrations/`, `runbooks/`, `processes/`, `environments/`, `.incidents/`, and `planning/roadmap.md`. Three new rule files: `planning-rules.md`, `incident-rules.md`, `runbook-rules.md`. The `frontmatter.enum.type` enum grows to cover PRD, RFC, ADR, incident, runbook, process, environment, integration.

### Removed

- `/memex:migrate-from-operations` command and backing `scripts/migrate_from_operations.py` — one-shot helper for migrating legacy Lumioh-style `.operations/` trees. No longer relevant; Memex is a standalone plugin.

---

## [0.1.0-alpha.1] — 2026-04-23

First public alpha. Full enforcement + session-lifecycle + wiki-operations loop, plus Unicode-friendly slugs and opt-in update notifications.

### Plugin core

- Manifest (`.claude-plugin/plugin.json`) + hook wiring (`hooks/hooks.json`) across `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `PreCompact`, `SessionEnd`.
- 16 Python hook scripts under `hooks/scripts/` + 8 shared `_lib/` helpers (config, paths, frontmatter, state, index parser, SemVer compare, glob-to-regex patterns, UTF-8 stderr bootstrap).

### Enforcement (PreToolUse)

- `path-guard.py` — `allowedTopLevel` whitelist, kebab-case, dated-folder format.
- `readme-required.py` — first write into a slug folder must be `README.md`.
- `doc-required.py` — warn-then-block when `codeToDocMapping` code lands without its linked doc.
- `ingest-doc-link.py` — migration-like artefacts must reference a wiki page or carry a `-- Doc:` header.
- `frontmatter-precheck.py` — non-blocking warning if an existing wiki page's frontmatter is already broken.

### Validation (PostToolUse)

- `frontmatter-check.py` — required fields + enum validation on matching pages.
- `index-update.py` — section-aware nudge when a new page isn't referenced from `index.md`.

### Session lifecycle

- `session-start-context.py` — injects `index.md` head + recent `log.md` entries.
- `user-prompt-context.py` — grep-first retrieval over the wiki; optional `qmd` integration with graceful fallback.
- `stop-log-append.py` / `stop-stale-check.py` / `stop-open-questions-check.py` — chronological logging, stale-doc flagging, inline-TODO detection.
- `precompact-snapshot.py` — session snapshot to `.memex/.state/sessions/` before compaction.
- `session-end-log.py` — final log entry.
- `update-check.py` (opt-in) — polls GitHub once every 24h for new releases. Off by default.

### Skills

`ingest-source`, `doc-query`, `wiki-lint`, `open-questions-triage`, `doc-refactor`.

### Subagents

`memex-ingestor` and `memex-linter` (worktree isolation), `memex-planner` (pre-task wiki read).

### Slash commands

`/memex:init`, `/memex:ingest`, `/memex:query`, `/memex:lint`, `/memex:log`, `/memex:open-q`, `/memex:promote`, `/memex:graph`.

### Profiles

- `engineering-ops` — SaaS / product codebases
- `research-wiki` — multi-source research (closest to Karpathy's gist)
- `book-companion` — reading a long book with the LLM
- `personal-journal` — private self-tracking
- `generic` — minimal starting point

Shared templates (`frontmatter.md.tmpl`, `agents.md.tmpl`, `claude.md.tmpl`) for authoring new profiles.

### Unicode support

- `path-guard` accepts lowercase / caseless letters from any Unicode script by default (Japanese, Chinese, Korean, Greek, Cyrillic, Arabic, Hebrew, Thai with combining marks, etc.). Extensions stay ASCII for file-system portability. Set `naming.asciiOnly: true` in `memex.config.json` to restrict to ASCII `[a-z0-9]`.

### Worked example

- `examples/research-wiki-demo/` — **fully-realised** post-ingest research wiki: one source in `raw/articles/`, its summary, extracted entity + two concept pages, one open question, updated index and log. `WALKTHROUGH.md` tells the full story. Verified by 35 contract tests.

### Schema

- `schemas/memex.config.schema.json` — JSON Schema for `memex.config.json` including every knob (`naming.asciiOnly`, `hookEvents.sessionStart.updateCheck`, `updateCheckUrl`, `search.engine`, etc.).

### Docs

- `README.md`, `CREDITS.md`, `CHANGELOG.md`, `docs/{README,concepts,hook-catalog,profile-authoring,cookbook}.md`.

### Governance

- `SECURITY.md` — threat model, reporting channels, SLAs.
- `CONTRIBUTING.md` — dev setup, coding conventions, PR checklist.
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.
- `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md`.

### CI & tooling

- `.github/workflows/ci.yml` runs `ruff` + `mypy` + `pytest` across Ubuntu / macOS / Windows on Python 3.10 and 3.12 for every push and PR.
- `pyproject.toml` declares `[project.optional-dependencies.dev]` for one-shot contributor setup (`pip install -e ".[dev]"`).
- `.gitignore` excludes `.env` / `.env.*.local` / `*.pem` / `*.key` / `*.p12` / `*.pfx` / `credentials.json` / `secrets.json` / `.aws/` / `.azure/` / `.gcp/` — safety net for forks.

### Test coverage

**227 pytest tests**, hermetic (no network; `update-check` uses a fixture override). Breakdown:

| File | Tests | What it covers |
|---|---|---|
| `test_hooks_pretooluse.py` | 21 | `path-guard`, `readme-required`, `doc-required`, `ingest-doc-link`, `frontmatter-precheck` |
| `test_hooks_posttooluse.py` | 9 | `frontmatter-check`, `index-update` |
| `test_hooks_session.py` | 13 | session-lifecycle + qmd-engine integration via mock binary |
| `test_unicode_paths.py` | 41 | Unicode kebab across 11+ writing systems + ASCII-only mode |
| `test_update_check.py` | 20 | SemVer compare + hook caching / TTL / failure modes |
| `test_demo_ingest.py` | 35 | contract verification for `examples/research-wiki-demo/` |
| `test_profiles.py` | 30 | profile scaffolds parametrised across 6 check types |
| `test_attribution.py` | 13 | Karpathy attribution present in every required file |
| `test_lib.py` | 34 | `_lib/*` unit tests (paths, frontmatter, index parse, patterns, config) |

`ruff check hooks/ tests/ scripts/` — clean. `mypy hooks/` — 0 issues across 23 files.

### Attribution

Inspired directly by Andrej Karpathy's [`llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026). The name nods to Vannevar Bush's 1945 Memex essay. Karpathy's gist is linked, not redistributed. Full attribution in [CREDITS.md](CREDITS.md).

### Known gaps

- **MCP server integration** — reading / writing the wiki from non-Claude clients. Not yet supported; tracked for v0.2.0.
