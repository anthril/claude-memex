---
title: Memex root (research-project)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# `.memex/` — research-project profile

This profile is tailored to projects that start as research + planning and will eventually migrate into development. A superset of `research-wiki`:

- **Research-wiki core:** `raw/` (immutable sources) \u2192 `wiki/` (LLM-authored knowledge). Same three operations — ingest, query, lint.
- **Planning-phase extras:** first-class `research/` (hypotheses, methodology, experiments, prompts, roadmap), plus `architecture/`, `systems/`, `evaluation/` for proposed-but-not-yet-built design.

See [AGENTS.md](AGENTS.md) for the binding contract. See [../memex.config.json](../memex.config.json) for the authoritative schema.

## Folder map

### Sources — immutable inputs

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

### Wiki — compounding LLM-authored knowledge

| Folder | Contents |
|---|---|
| `wiki/entities/<slug>/README.md` | Named things: people, orgs, products, places |
| `wiki/concepts/<slug>/README.md` | Abstract ideas, frameworks, methodologies |
| `wiki/summaries/<slug>.md` | One page per raw source — what it says, key claims |
| `wiki/analyses/<slug>.md` | User-driven explorations filed back (from `/memex:query`) |
| `wiki/syntheses/<slug>.md` | Cross-source synthesis pages |

### Research — first-class research artefacts

| Folder | Contents |
|---|---|
| `research/roadmap.md` | Rolling research roadmap. Edit freely. |
| `research/hypotheses/<slug>.md` | Stated, testable hypotheses with predicted outcomes |
| `research/literature-review/<slug>.md` | Literature survey docs grouped by topic |
| `research/methodology/<slug>.md` | Experimental methodology, evaluation protocols |
| `research/experiments/<slug>/README.md` | One folder per experiment — design, data, results |
| `research/prompts/<slug>.md` | Prompts, interview scripts, protocol questions |

### Planning — pre-implementation design

| Folder | Contents |
|---|---|
| `architecture/<slug>/README.md` | High-level architectural / design documents for the proposed system |
| `systems/<slug>/README.md` | Planned or in-progress subsystems — specs, interfaces, dependencies |
| `evaluation/<slug>/README.md` | Evaluation plans, benchmarks, success criteria |

### Infrastructure — every profile has these

| Folder | Contents |
|---|---|
| `.open-questions/<slug>.md` | Unresolved cross-cutting questions |
| `.rules/*.md` | Project-specific rule documents |
| `.state/` | Plugin-managed per-session state |
| `index.md` | Auto-maintained catalogue |
| `log.md` | Auto-appended chronological ledger |

## The three operations

- **Ingest** — `/memex:ingest <path>`. The LLM reads a `raw/` source, writes a `wiki/summaries/` page, updates `wiki/entities/` and `wiki/concepts/`, bumps the index, appends the log.
- **Query** — `/memex:query <question>`. The LLM searches the index, reads relevant pages, synthesises a cited answer. Good answers get filed back as `wiki/analyses/`.
- **Lint** — `/memex:lint`. Orphans, contradictions, stale claims, missing cross-refs.

## Research-to-development transition

Projects in this profile eventually enter active development. See [`.rules/research-to-development.md`](.rules/research-to-development.md) for which surfaces "graduate" when that happens — for example, `systems/<slug>/` becomes `platform/systems/<slug>/` under an engineering-ops overlay, `architecture/` folds into `planning/rfcs/` + `planning/decisions/`, and `research/experiments/` archive to `.research/<DDMMYYYY-HHMM>/`.

When ready, run `/memex:init-profile engineering-ops` — the profile-builder skill will propose an overlay that preserves the research tree while adding engineering-ops surfaces.
