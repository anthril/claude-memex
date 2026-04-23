---
description: Ask a question against the Memex wiki
argument-hint: "<question>"
allowed-tools: Read, Write, Grep, Glob, Bash
---

# /memex:query

Synthesise a cited answer from the wiki. Thin wrapper over the `doc-query` skill.

## Usage

```
/memex:query What do we know about authentication flows?
/memex:query list all open questions tagged billing
/memex:query what's the latest on the migration plan?
```

## Behaviour

Invokes the `doc-query` skill:

1. Read `index.md`
2. Search (grep or qmd)
3. Read top candidate pages in full
4. Synthesise with inline citations
5. Offer to file the answer back as `<root>/wiki/analyses/<slug>.md` (or `analyses/<slug>.md` per profile) for compounding value

If no matches found, print the search terms used, suggest which `raw/` or external source might fill the gap, and offer to file the question as `.open-questions/<slug>.md`.

See [`../skills/doc-query/SKILL.md`](../skills/doc-query/SKILL.md) for the full flow.
