---
description: Ingest a raw source into the Memex wiki
argument-hint: "<path-to-source>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

# /memex:ingest

Ingest a raw source into the wiki. Thin wrapper over the `ingest-source` skill.

## Usage

```
/memex:ingest .memex/raw/articles/some-article.md
/memex:ingest ~/Downloads/report.pdf
/memex:ingest https://example.com/blog/post   # fetch first, then ingest
```

## Behaviour

1. Resolve the path. If it's a URL, ask the user whether to fetch (`WebFetch`) or whether they'll clip it manually first.
2. If the source is large (> 20k chars) OR it's a multi-part source (directory, several files), **delegate to the `memex-ingestor` subagent** for isolation.
3. Otherwise, invoke the `ingest-source` skill directly in-session.

## What happens

See [`../skills/ingest-source/SKILL.md`](../skills/ingest-source/SKILL.md) for the full 10-step workflow. Summary:

1. Load `memex.config.json`, `index.md`, `log.md`
2. Read the source in full
3. Discuss key takeaways with the user
4. Write summary page
5. Extract and update entity/concept pages
6. Update cross-references
7. File cross-cutting open questions
8. Update `index.md`
9. Append `log.md`
10. Present diff summary

## Failure modes

- Source file doesn't exist → print path and stop
- Source already summarised (summary page exists at the predicted path) → ask the user whether to re-ingest (overwriting) or skip
- Profile has no summary folder convention → use `topics/<slug>/README.md` as a safe default and log the convention gap
