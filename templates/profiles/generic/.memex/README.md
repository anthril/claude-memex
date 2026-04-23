---
title: Memex root (generic)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# `.memex/` — generic profile

Minimal Claude-maintained wiki. See [AGENTS.md](AGENTS.md) for the contract. See [../memex.config.json](../memex.config.json) for the schema.

## Folders

| Folder | Contents |
|---|---|
| `topics/<slug>/README.md` | One folder per topic — any coherent subject you want to accumulate knowledge about |
| `.open-questions/` | Unresolved cross-cutting questions |
| `.rules/` | Project-specific rule documents |
| `index.md` | Auto-maintained catalogue |
| `log.md` | Auto-appended ledger |

## Starting out

1. Pick a topic (`topics/my-topic/`) and have Claude write the first `README.md`
2. Add sources (paste, cite, or reference)
3. Ask questions; let Claude update the page
4. Add `## Open questions` sections as they surface

When your wiki outgrows this profile, consider switching to `engineering-ops`, `research-wiki`, `book-companion`, or `personal-journal`.
