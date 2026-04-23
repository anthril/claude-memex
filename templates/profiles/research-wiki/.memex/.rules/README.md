---
title: Rules (research-wiki)
slug: rules-index
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Rules

Project-specific conventions. The default set below is thin — extend as your wiki grows.

## Frontmatter requirements

All pages under `wiki/**/*.md` and all `README.md` / `AGENTS.md` files require:

```yaml
title: Human-readable title
slug: kebab-case-slug
type: entity|concept|summary|analysis|synthesis|open-question|rule
status: draft|active|deprecated
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

## Naming

- Folders under `wiki/entities/` and `wiki/concepts/` use kebab-case
- Summary/analysis/synthesis files use kebab-case with optional ordering prefix (`01-foo.md`)

## Cross-linking

- Entity and concept pages cross-link to every source summary that mentions them
- Summary pages cross-link to the entities and concepts they introduce or extend
- Analyses cite every page they synthesise from

## Sources in `raw/`

- `raw/` is immutable. Do not rewrite, reformat, or "clean up" source files.
- If a source needs corrections (OCR errors, missing context), document them in the summary, not the source.
- Binary assets live under `raw/assets/`. Prefer local copies over URLs for images you want the LLM to view.
