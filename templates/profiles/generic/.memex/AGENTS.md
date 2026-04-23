---
title: Agent Contract (generic)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Agent Contract

This wiki uses the `generic` Memex profile — a minimal starting point.

## Folders

- `topics/<slug>/README.md` — one folder per topic
- `.open-questions/<slug>.md` — unresolved items
- `index.md` — auto-maintained catalogue
- `log.md` — auto-appended ledger

## Rules

1. All pages carry YAML frontmatter (`title`, `slug`, `type`, `status`, `created`, `updated`)
2. Paths are kebab-case
3. New `topics/<slug>/` folders must start with `README.md`
4. No inline TODOs — file them under `.open-questions/`

This profile is intentionally lean. Fork it (`templates/profiles/generic/` → your own) to add structure as your wiki grows.

---

*This contract derives from [Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).*
