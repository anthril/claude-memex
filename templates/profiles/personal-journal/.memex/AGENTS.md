---
title: Agent Contract (personal-journal)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Agent Contract

A private, long-running journal. The LLM helps you accumulate self-knowledge across journal entries, podcast notes, article summaries — building a structured picture of yourself over time.

## Folders

- `raw/entries/<DDMMYYYY-HHMM>/` — one folder per raw journal entry / note / article clip
- `wiki/topics/<slug>/README.md` — accumulated topics (e.g. health, career, a relationship, a skill)
- `wiki/goals/<slug>/README.md` — goals being tracked, with status history
- `reflections/<DDMMYYYY-HHMM>/` — periodic reflection pages (LLM-synthesised)
- `index.md`, `log.md`, `.open-questions/`

## Privacy

This profile assumes the wiki is private. Do NOT enable any sync, cloud-upload, or telemetry features without the user's explicit consent. The `.memex/` tree should be in a git repo the user controls, or not in a repo at all.

## Workflow

- Write / paste an entry into `raw/entries/<timestamp>/entry.md`
- `/memex:ingest` it — the LLM updates `wiki/topics/` with anything that fits
- Weekly / monthly: prompt for a reflection via the `doc-query` skill, offer to file as `reflections/<timestamp>/reflection.md`

## Forbidden

- Telling the user what to feel or concluding character judgements — the LLM summarises, cross-references, and asks questions, not therapises
- Speculation in `wiki/topics/` beyond what the entries support — surface uncertainty as `## Open questions` instead

---

*Inspired by [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), first use case listed: "Personal — tracking your own goals, health, psychology, self-improvement."*
