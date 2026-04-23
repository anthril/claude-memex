# Concepts

This document fixes the terminology and explains why Memex is structured the way it is.

---

## The three-layer model

This is inherited directly from [Karpathy's `llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

**Raw sources.** Your curated collection of source documents. Articles, papers, images, meeting transcripts, design docs. Immutable. The LLM reads from them but never modifies them. In the `engineering-ops` profile, "raw" is the actual codebase — the LLM reads the code but the wiki layer is separate. In `research-wiki`, raw lives under `.memex/raw/`.

**The wiki.** A directory of LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this layer entirely. You read it; the LLM writes it. Lives under `.memex/` in every profile.

**The schema.** `memex.config.json` + the rules files under `.memex/.rules/`. Tells the LLM how the wiki is structured, what the conventions are, what workflows to follow. The hooks read the schema — the LLM reads the rules. This is what makes the LLM a disciplined wiki maintainer rather than a generic chatbot.

---

## The three operations

Also inherited from the gist:

**Ingest.** New source arrives. The LLM reads it, summarises, extracts entities/concepts, updates every relevant page (not just the new summary), appends `log.md`, bumps `index.md`. A single source can touch 10–15 pages.

**Query.** You ask a question. The LLM reads `index.md`, finds relevant pages, reads them, synthesises a cited answer. Good answers get filed back as new analysis pages so the exploration compounds.

**Lint.** Periodic health-check. Orphan pages, contradictions, stale claims, missing cross-refs, open questions overdue, data gaps. The LLM proposes auto-fixes for the easy ones.

---

## Why hooks, not prompts

Prompts are advisory. Hooks are mandatory.

Tell Claude in `CLAUDE.md` that "all docs go in `.memex/`" and you'll find `src/notes.md` and `TODO.txt` in your tree within a week. Hooks that return `exit 2` with a clear stderr message when Claude tries to write a doc in the wrong place are ~100× more effective, because they interrupt the tool call and surface the rule directly to Claude's next turn.

This is the single biggest lesson that separates Memex from doc conventions written into CLAUDE.md.

---

## Why the schema is a file

The hook logic is project-agnostic; the rules it enforces are project-specific. Decoupling the two keeps the plugin portable.

`memex.config.json` declares the taxonomy — allowed folders, required frontmatter, code-to-doc mappings. The same `path-guard.py` that blocks `src/notes.md` in an engineering-ops-shaped project blocks `raw/scratchpad/` in a research-wiki project, because both derive their rules from the config.

This is the key abstraction that makes Memex reusable across very different kinds of knowledge base.

---

## Index and log

Two special files, one per profile, both auto-maintained.

**`index.md`** is content-oriented. A catalogue of every wiki page, grouped by category (entities, concepts, features, systems, open questions, recent activity). The `UserPromptSubmit` hook reads it to find relevant pages for a user question. The `PostToolUse` hook nudges Claude to update it on every new page.

**`log.md`** is chronological. Append-only. The `Stop` hook appends an entry every session. Entries use a parseable prefix:

```
## [YYYY-MM-DD] event | subject
```

This makes the log tractable with plain Unix tools. `grep "^## \[" log.md | tail -5` shows the last five entries. `grep "^## \[" log.md | grep ingest | wc -l` counts ingests.

---

## Open questions as first-class artifacts

Inline `TODO` / `TBD` in prose is banned. Every unresolved question gets promoted to one of two places:

- **Cross-cutting:** `.memex/.open-questions/<slug>.md` — gets its own file with frontmatter
- **Scoped:** a `## Open questions` section on the owning page

The `Stop` hook greps the session's writes for inline TODO markers and prompts Claude to promote them. The `open-questions-triage` skill groups them by topic / age and proposes resolutions.

Resolved questions move to `.open-questions/.resolved/`. Nothing is deleted — the question and its resolution are both valuable forensic artefacts.

---

## Frontmatter is non-negotiable

Every page in `.memex/` has YAML frontmatter with at minimum:

```yaml
---
title: Human-readable title
slug: kebab-case-identifier
type: feature|system|entity|concept|summary|synthesis|open-question|rule
status: draft|active|deprecated
owner: person-or-team
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Validated by `PostToolUse`. Missing fields → `exit 2` → Claude fixes and retries. The field set is profile-specific — the `frontmatter.required` list in `memex.config.json` is authoritative.

Dataview-compatible by design. If you use Obsidian with Dataview, tables that query over status / type / owner work out of the box.

---

## Prior art & influences

| Input | What it contributed |
|---|---|
| Andrej Karpathy's [`llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026) | **The conceptual origin.** Three-layer model, three operations, index + log, compounding synthesis, Obsidian-as-IDE. |
| Vannevar Bush's "As We May Think" (1945) | The name. The vision of a private, curated, cross-referenced personal knowledge store. |
| Anthropic's `claude-md-management` plugin | Complementary tool. Handles the one-file CLAUDE.md problem; Memex handles the multi-page tree. Use both. |
| `qmd` by Tobias Lütke | Optional on-device BM25 + vector search over markdown. Memex falls back to grep; if `qmd` is installed and enabled in config, the `user-prompt-context` hook shells out to it. |

What each gets attribution for in the codebase is listed in [CREDITS.md](../CREDITS.md).

---

## What Memex doesn't do

- **No embedding pipeline by default.** Grep-on-index works to ~100 sources per Karpathy's note. Larger wikis opt into `qmd`.
- **No doc generation from code.** Memex doesn't autogenerate docs from type signatures or commit messages. It enforces a tree the LLM writes; the LLM does the synthesis.
- **No sync with external systems.** No Notion bridge, no Confluence connector, no Slack ingestor in v1. Those are natural extensions for later versions.
- **No replacement for `CLAUDE.md`.** The management plugin and Memex solve different problems.
- **No hand-rolled RAG infrastructure.** The `user-prompt-context` hook is the entire retrieval layer in v1 — grep over `index.md` + frontmatter, optionally upgraded with `qmd`.
