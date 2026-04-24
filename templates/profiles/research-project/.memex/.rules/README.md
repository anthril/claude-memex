---
title: Rules (research-project)
slug: rules-index
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Rules

Project-specific conventions. Extend as the project grows.

## Files

| File | Purpose |
|---|---|
| [research-to-development.md](research-to-development.md) | How surfaces graduate from planning into active development |

## Frontmatter requirements

All pages under `wiki/**/*.md`, `research/**/*.md`, `architecture/**/*.md`, `systems/**/*.md`, `evaluation/**/*.md`, and all `README.md` / `AGENTS.md` files require:

```yaml
title: Human-readable title
slug: kebab-case-slug
type: entity|concept|summary|analysis|synthesis|hypothesis|methodology|literature-review|experiment|prompt|architecture|system|evaluation|open-question|rule
status: draft|active|deprecated
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

## Naming

- Folders under `wiki/entities/`, `wiki/concepts/`, `research/experiments/`, `architecture/`, `systems/`, `evaluation/` use kebab-case
- Flat-file artefacts (hypotheses, methodology, literature-review, prompts, summaries, analyses, syntheses) use kebab-case with an optional ordering prefix (`01-foo.md`)

## Cross-linking

- Every hypothesis links to the experiment(s) testing it; every experiment back-links to its hypothesis
- Every system design links to the entities and concepts it involves
- Every evaluation plan links to the hypothesis or system it evaluates
- Every analysis cites every page it synthesises from

## Sources in `raw/`

- `raw/` is immutable. Do not rewrite, reformat, or "clean up" source files.
- If a source needs corrections (OCR errors, missing context), document them in the summary, not the source.
- Binary assets live under `raw/assets/`. Prefer local copies over URLs for images you want the LLM to view.

## Experiment discipline

- Every experiment has a linked hypothesis BEFORE data is collected
- Results are reported even if they refute the hypothesis — especially if they refute the hypothesis
- Null results are valuable; a `status: deprecated` hypothesis with a well-documented refutation experiment is a win
