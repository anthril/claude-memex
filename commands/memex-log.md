---
description: View or edit the Memex log
argument-hint: "[--tail N] [--edit]"
allowed-tools: Read, Edit, Bash
---

# /memex:log

View the chronological ledger or add a manual entry.

## Usage

```
/memex:log              # print whole log
/memex:log --tail 5     # print last 5 entries (parseable prefix → easy to slice)
/memex:log --edit       # open log.md for a manual entry, appended with today's date
```

## Behaviour

1. Locate `memex.config.json` (walk up from cwd). Read `log.path` — default `log.md` under the ops root.
2. If no args: print the whole file.
3. If `--tail N`: use `grep "^## \[" <path> | tail -N` semantics — find the last N entries delimited by `## [YYYY-MM-DD]` prefix, including their bodies.
4. If `--edit`: append a new entry stub using the `log.entryPrefix` template (default `## [{date}] {event} | {subject}`). Prompt the user for `event` and `subject`. Do NOT auto-fill — the user writes these.

Do not rewrite or reorder the log. Entries are append-only by contract.
