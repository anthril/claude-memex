---
title: Memex root (personal-journal)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# `.memex/` — personal-journal profile

Private, long-running self-tracking wiki. See [AGENTS.md](AGENTS.md).

## Folders

| Folder | Contents |
|---|---|
| `raw/entries/<timestamp>/` | Journal entries, podcast notes, article clips, anything raw |
| `wiki/topics/<slug>/README.md` | Accumulated topics (health, career, a relationship, a skill) |
| `wiki/goals/<slug>/README.md` | Tracked goals with status history |
| `reflections/<timestamp>/` | LLM-synthesised periodic reflections |
| `index.md`, `log.md`, `.open-questions/` | Standard |

## Privacy

Keep this repo private. The wiki should live somewhere you control; do not push to a public remote by accident.

## Suggested rhythm

- **Daily (or when inspired):** drop an entry into `raw/entries/<timestamp>/entry.md`; `/memex:ingest` it
- **Weekly:** `/memex:query "what's notable in entries from the past week?"` → file the answer as a reflection
- **Monthly:** `/memex:lint` for contradictions / stale topics; review goals
