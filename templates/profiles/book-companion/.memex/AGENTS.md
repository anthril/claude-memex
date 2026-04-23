---
title: Agent Contract (book-companion)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Agent Contract

This wiki accompanies reading a long book. One chapter at a time, the LLM extracts characters, places, themes, and plot threads; updates their pages as the narrative progresses; flags contradictions or unresolved arcs.

## Folders

- `raw/chapters/<NN>-<slug>.md` — one file per chapter with the text (or a summary if you prefer a lighter touch)
- `wiki/characters/<slug>/README.md` — one folder per character
- `wiki/places/<slug>/README.md` — one folder per place
- `wiki/themes/<slug>/README.md` — one folder per theme
- `wiki/plot-threads/<slug>/README.md` — one folder per narrative thread
- `timeline.md` — event chronology across chapters
- `index.md`, `log.md`, `.open-questions/` — as always

## Workflow

- Per chapter: `/memex:ingest .memex/raw/chapters/<NN>-<slug>.md`
- The LLM reads the chapter, updates characters they appear in, updates places they visit, threads they progress, themes they develop, appends to `timeline.md`
- Cross-references accumulate — e.g. Character A's page lists every chapter she appears in

## Forbidden

- Spoilers in a character's bio beyond the chapters read so far (the LLM must track reading progress)
- Editing `raw/chapters/` (the text is canonical)
- Writing plot predictions as facts

## Reading progress

Track reading progress in `log.md` — the most recent `## [YYYY-MM-DD] read | chapter NN` entry is the horizon. The LLM only writes to wiki pages using information from chapters up to that horizon.

---

*Inspired by [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — in particular its example of using this pattern for reading a book with the LLM.*
