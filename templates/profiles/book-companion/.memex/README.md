---
title: Memex root (book-companion)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# `.memex/` — book-companion profile

Companion wiki for reading a long book. Like a fan wiki but built by you and the LLM as you read.

See [AGENTS.md](AGENTS.md) for the contract.

## Folder map

| Folder | Contents |
|---|---|
| `raw/chapters/<NN>-<slug>.md` | Chapter text (or condensed summary) |
| `wiki/characters/<slug>/README.md` | Character profile, appearances, relationships |
| `wiki/places/<slug>/README.md` | Place description, first appearance, significance |
| `wiki/themes/<slug>/README.md` | Theme traces across chapters |
| `wiki/plot-threads/<slug>/README.md` | Narrative threads — set up, developed, paid off |
| `timeline.md` | Event chronology (in-universe time, not chapter order if they differ) |
| `index.md` | Catalogue |
| `log.md` | Reading progress + ingest events |

## Suggested workflow

1. Read chapter N
2. `/memex:ingest .memex/raw/chapters/<NN>-<slug>.md` (or paste the chapter summary into a new raw file, then ingest)
3. Review the updates — characters introduced, places visited, threads advanced
4. `/memex:query` anytime — "who are all the characters mentioned in chapters 1–5 who haven't reappeared?"
5. At reading milestones, `/memex:lint` to catch contradictions
