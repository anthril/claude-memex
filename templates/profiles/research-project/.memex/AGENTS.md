---
title: Agent Contract (research-project)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Agent Contract

Binding contract for agents operating on this research-project wiki.

Inspired by [Andrej Karpathy's `llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The LLM writes and maintains the wiki; the human curates sources, asks questions, proposes hypotheses, reviews.

## 1. Before starting work

1. Read [README.md](README.md) for the folder map
2. Read [index.md](index.md) — catalogue of current pages
3. Check [`.open-questions/`](.open-questions/) for the topic
4. Check [`.project-owner-actions/`](.project-owner-actions/) for owner-only blockers that touch your task — if your work is gated on one, surface it before going further
5. Read [`.rules/`](.rules/) for project-specific conventions — especially [`research-to-development.md`](.rules/research-to-development.md) if you're about to propose moving a surface from planning into code

## 2. The three layers (plus two)

| Layer | Mutable by LLM? | Purpose |
|---|---|---|
| `raw/` | No (read-only) | Immutable source documents |
| `wiki/` | Yes (everywhere) | LLM-authored markdown — compounding knowledge |
| `research/` | Yes | First-class research artefacts (hypotheses, methodology, experiments) |
| `architecture/`, `systems/`, `evaluation/` | Yes | Pre-implementation design — what we plan to build |
| `memex.config.json` + `.rules/` | Only with explicit user approval | Schema |

## 3. Required artifacts

| Trigger | Required doc |
|---|---|
| New source in `raw/` processed | `wiki/summaries/<source-slug>.md` |
| New named entity mentioned | `wiki/entities/<slug>/README.md` |
| New abstract concept | `wiki/concepts/<slug>/README.md` |
| User's question with valuable answer | `wiki/analyses/<slug>.md` (offer to file back) |
| Cross-source synthesis | `wiki/syntheses/<slug>.md` |
| New testable claim about the system | `research/hypotheses/<slug>.md` |
| Literature survey on a topic | `research/literature-review/<slug>.md` |
| New experimental protocol | `research/methodology/<slug>.md` |
| New experiment being designed or run | `research/experiments/<slug>/README.md` |
| New prompt or interview script | `research/prompts/<slug>.md` |
| New architectural proposal | `architecture/<slug>/README.md` |
| New proposed subsystem | `systems/<slug>/README.md` |
| New evaluation plan or benchmark | `evaluation/<slug>/README.md` |
| Unresolved cross-cutting question | `.open-questions/<slug>.md` |

All pages require full frontmatter (`title`, `slug`, `type`, `status`, `created`, `updated`).

## 4. Hypothesis discipline

- Every hypothesis is **falsifiable**. State what observation would refute it.
- Every hypothesis has a **predicted outcome** before the experiment, not after.
- When an experiment concludes, update the linked hypothesis's `status:` to `active` (supported) or `deprecated` (refuted). Never silently delete.

## 5. Experiment discipline

- Every `research/experiments/<slug>/README.md` follows the structure:

```markdown
# <experiment name>

## Question
The specific question this experiment answers.

## Linked hypothesis
[Link to research/hypotheses/<slug>.md]

## Design
Setup, variables, controls, success criteria.

## Protocol
Step-by-step. Reproducible by a different researcher.

## Data
Link to raw data under raw/datasets/ or attached files. Include capture date.

## Results
What actually happened. Numbers, not narrative.

## Conclusion
Does the evidence support or refute the hypothesis? With what confidence?

## Next steps
Follow-up experiments, refinements, or pivots.
```

## 6. Cross-references

Every wiki page links to:

- The sources that informed it (`raw/`)
- Related entities / concepts
- If applicable: the hypothesis it tests, or the experiment that produced it
- From its parent index section

The `wiki-lint` skill catches missing links.

## 7. Forbidden actions

- Writing inside `raw/` (immutable)
- Leaving TODO / TBD markers inline — file them under `.open-questions/`
- Deleting wiki pages without a `/memex:promote` or `doc-refactor` flow — preserve provenance
- Editing `memex.config.json` without filing an open question explaining why
- Adding results to a hypothesis retroactively without marking status change

## 8. Compounding, not rediscovery

When ingesting a new source, **update every relevant existing page**, not just the new summary. If a new source contradicts an existing claim, flag the contradiction prominently on both pages — and consider whether a hypothesis is now refuted.

---

*This contract derives from [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). See the plugin's [CREDITS.md](https://github.com/anthril/claude-memex/blob/main/CREDITS.md).*
