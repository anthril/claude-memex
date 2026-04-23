# Memex — Documentation

This folder documents the plugin itself.

---

## Start here

| Document | What it covers |
|---|---|
| [concepts.md](concepts.md) | Terminology, architecture, prior art, the three-layer model (raw / wiki / schema) |
| [hook-catalog.md](hook-catalog.md) | Every hook Memex ships, when it fires, what it enforces, how it fails |
| [profile-authoring.md](profile-authoring.md) | How to write a new profile (scaffolded template tree + `memex.config.json`) |
| [cookbook.md](cookbook.md) | Recipes: adding a custom folder, disabling a hook, extending the schema, migrating from Lumioh `.operations/` |

See also: [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for development setup and coding conventions; [`../SECURITY.md`](../SECURITY.md) for the security policy; [`../CHANGELOG.md`](../CHANGELOG.md) for release notes.

---

## Command reference

Slash commands shipped by the plugin. All are namespaced under `/memex:`.

| Command | Signature | What it does |
|---|---|---|
| `/memex:init` | `/memex:init [profile]` | Scaffolds `.memex/`, `memex.config.json`, and appends to `CLAUDE.md`. Refuses to overwrite. Default profile: `generic`. |
| `/memex:ingest` | `/memex:ingest <path>` | Reads a raw source, summarises to the wiki, updates entity pages, bumps `index.md`, appends `log.md`. |
| `/memex:query` | `/memex:query <question>` | Searches wiki by index → reads matching pages → synthesises a cited answer. Offers to file the answer back. |
| `/memex:lint` | `/memex:lint [scope]` | Health-check: orphans, contradictions, stale claims, missing cross-refs, TODOs inline. |
| `/memex:log` | `/memex:log [--tail N] [--edit]` | Prints recent log; `--edit` opens for manual entry. |
| `/memex:open-q` | `/memex:open-q <title>` | Files a new open question under `.memex/.open-questions/` with the profile's template. |
| `/memex:promote` | `/memex:promote <doc-path> <type>` | Promotes a `.research/` or `raw/` snippet to a permanent entity / concept / feature page. |
| `/memex:graph` | `/memex:graph [--format mermaid\|dot]` | Emits a link graph. Feeds the "is this orphaned?" view. |
| `/memex:migrate-from-operations` | `/memex:migrate-from-operations [--dry-run]` | One-shot helper: rewrites `.operations/` → `.memex/` and extracts matching `memex.config.json`. `--dry-run` previews without changing anything. Backed by `scripts/migrate_from_operations.py` (tested). |

---

## Skills

Skills are **auto-invoked** by Claude when the conversation context matches their trigger phrases. You don't call them directly; the slash command above is usually a thin wrapper around the corresponding skill.

| Skill | Triggered by |
|---|---|
| `ingest-source` | "ingest this", "process this article", paths into `.memex/raw/` |
| `doc-query` | "what does the wiki say about", "based on my docs" |
| `wiki-lint` | "lint the wiki", "audit my docs", "health-check the wiki" |
| `open-questions-triage` | "triage open questions", "what's blocking me" |
| `doc-refactor` | "split this page", "merge these", "rename this slug" |

---

## Subagents

| Agent | Used for |
|---|---|
| `memex-ingestor` | Large or multi-part source ingests. Runs in worktree isolation so long ingests don't bloat the main session context. |
| `memex-linter` | Wiki-lint passes on large wikis. Returns summary; original context stays clean. |
| `memex-planner` | Pre-task planning: reads relevant wiki pages + open questions, produces a plan. |

---

## Configuration

Every Memex-enabled project has a `memex.config.json` at its root (or inside `.memex/` — both paths are checked). This file drives every hook. See [`../schemas/memex.config.schema.json`](../schemas/memex.config.schema.json) for the full schema.

Minimal config:

```json
{
  "$schema": "https://raw.githubusercontent.com/anthril/claude-memex/main/schemas/memex.config.schema.json",
  "version": "1",
  "profile": "generic",
  "root": ".memex"
}
```

See [profile-authoring.md](profile-authoring.md) for how to extend it.
