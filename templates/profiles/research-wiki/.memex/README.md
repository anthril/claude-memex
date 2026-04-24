---
title: Memex root (research-wiki)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# `.memex/` — research-wiki profile

This profile is the most literal adaptation of [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — three layers, three operations, compounding synthesis.

- **Raw layer:** `raw/` — immutable sources. Articles, papers, transcripts, images.
- **Wiki layer:** `wiki/` — LLM-authored markdown. Entities, concepts, summaries, analyses, syntheses.
- **Schema layer:** [`../memex.config.json`](../memex.config.json) + [AGENTS.md](AGENTS.md) — the contract.

## Folder map

| Folder | Contents |
|---|---|
| `raw/articles/` | Web articles (Obsidian Web Clipper output, pasted content) |
| `raw/papers/` | PDFs, academic papers |
| `raw/books/` | Book excerpts, chapters, entire books |
| `raw/transcripts/` | Podcast / talk / lecture / meeting transcripts |
| `raw/videos/` | Video references (link files, caption extracts) |
| `raw/interviews/` | User interviews, expert interviews, Q&A transcripts |
| `raw/standards/` | RFCs, W3C / ISO standards, regulatory documents |
| `raw/datasets/` | CSV / JSON reference datasets, experimental data |
| `raw/notes/` | User's own notes, scratch work, field notes |
| `raw/assets/` | Images, diagrams, supporting binaries |
| `wiki/entities/<slug>/README.md` | Named things: people, orgs, products, places |
| `wiki/concepts/<slug>/README.md` | Abstract ideas, frameworks, methodologies |
| `wiki/summaries/<slug>.md` | One page per raw source — what it says, key claims |
| `wiki/analyses/<slug>.md` | User-driven explorations filed back (from `/memex:query`) |
| `wiki/syntheses/<slug>.md` | Cross-source synthesis pages |
| `.open-questions/<slug>.md` | Unresolved items |
| `index.md` | Auto-maintained catalogue |
| `log.md` | Auto-appended ledger |

## The three operations

- **Ingest** — `/memex:ingest <path>`. The LLM reads a `raw/` source, writes a `wiki/summaries/` page, updates `wiki/entities/` and `wiki/concepts/`, bumps the index, appends the log.
- **Query** — `/memex:query <question>`. The LLM searches the index, reads relevant pages, synthesises a cited answer. Good answers get filed back as `wiki/analyses/`.
- **Lint** — `/memex:lint`. Orphans, contradictions, stale claims, missing cross-refs.

## Tooling notes

- **Obsidian** is the recommended IDE. Frontmatter is Dataview-compatible.
- **Obsidian Web Clipper** converts web articles to markdown. Drop them into `raw/articles/`.
- **qmd** — optional local BM25 + vector search. Set `search.engine: "qmd"` in the config to enable.
