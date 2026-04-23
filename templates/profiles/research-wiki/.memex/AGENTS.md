---
title: Agent Contract (research-wiki)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Agent Contract

Binding contract for agents operating on this research wiki.

Inspired directly by [Andrej Karpathy's `llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The LLM writes and maintains the wiki; the human curates sources, asks questions, reviews.

## 1. Before starting work

1. Read [README.md](README.md) for the folder map
2. Read [index.md](index.md) — catalogue of current pages
3. Check [`.open-questions/`](.open-questions/) for the topic
4. Read `.rules/*` for project-specific conventions

## 2. The three layers

| Layer | Mutable by LLM? | Purpose |
|---|---|---|
| `raw/` | No (read-only) | Immutable source documents |
| `wiki/` | Yes (everywhere) | LLM-authored markdown |
| `memex.config.json` + `.rules/` | Only with explicit user approval | Schema |

## 3. Required artifacts

| Trigger | Required doc |
|---|---|
| New source in `raw/` processed | `wiki/summaries/<source-slug>.md` |
| New named entity mentioned | `wiki/entities/<slug>/README.md` |
| New abstract concept | `wiki/concepts/<slug>/README.md` |
| User's question with valuable answer | `wiki/analyses/<slug>.md` (offer to file back) |
| Cross-source synthesis | `wiki/syntheses/<slug>.md` |
| Unresolved cross-cutting question | `.open-questions/<slug>.md` |

All pages carry full frontmatter (`title`, `slug`, `type`, `status`, `created`, `updated`).

## 4. Cross-references

Every wiki page links to the sources that informed it, to related entities/concepts, and from its parent index section. The `wiki-lint` skill catches missing links.

## 5. Forbidden actions

- Writing inside `raw/` (it's immutable)
- Leaving TODO/TBD markers inline — file them under `.open-questions/`
- Deleting wiki pages without an `/memex:promote` or `doc-refactor` flow — preserve provenance
- Editing `memex.config.json` without filing an open question explaining why

## 6. Compounding, not rediscovery

When ingesting a new source, **update every relevant existing page**, not just the new summary. The wiki's value is that claims have been cross-linked and synthesised once — don't re-derive. If a new source contradicts an existing claim, flag the contradiction prominently on both pages.

---

*This contract derives from [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). See the plugin's [CREDITS.md](https://github.com/anthril/claude-memex/blob/main/CREDITS.md).*
