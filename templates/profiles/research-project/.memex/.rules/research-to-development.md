---
title: Research-to-development transition
slug: research-to-development
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Research-to-development transition

Projects scaffolded with `research-project` start in planning/research phase. When the team starts to actually build — write production code, ship features, stand up infrastructure — the wiki needs to evolve. This rule describes that evolution.

## When to transition

Signals that the project is entering active development:

- A runnable prototype exists and is being iterated, not thrown away
- The team is writing tests, not just experiments
- There's a deployment target (staging, production, user install)
- The first "real" user is about to touch the system
- A CI pipeline is being wired up

If any three of these are true, it's time to overlay engineering-ops.

## How to transition

Run `/memex:init-profile engineering-ops` in the project root. The profile-builder skill will detect the existing `research-project` scaffold and propose an **overlay**, not an overwrite:

1. Preserve the entire `research/`, `architecture/`, `systems/`, `evaluation/` trees
2. Add engineering-ops top-levels (`planning/`, `platform/`, `workers/`, `agents/`, `workflows/`, `runbooks/`, `processes/`, `environments/`, `.incidents/`, `.audits/`, `.research/`)
3. Merge `frontmatter.enum.type` so both profiles' types are allowed
4. Extend `allowedTopLevel` with the engineering-ops surfaces

You end up with a hybrid `memex.config.json` where both trees coexist.

## Graduation map

How each research-project surface eventually relates to engineering-ops:

| Research-project surface | Engineering-ops counterpart | Migration |
|---|---|---|
| `research/hypotheses/` | *(no direct counterpart)* | Keep as history. New hypotheses still go here. |
| `research/literature-review/` | *(no direct counterpart)* | Keep as-is. |
| `research/methodology/` | *(no direct counterpart)* | Keep as-is; relevant for ongoing evaluation. |
| `research/experiments/<slug>/` | `.research/<DDMMYYYY-HHMM>/` | Completed experiments may be archived into the dated folder once the system they tested has been built. |
| `research/prompts/` | `platform/features/*/README.md` "Prompts" section | When a prompt becomes production, fold it into the feature doc. Keep the `research/prompts/` version as historical provenance. |
| `research/roadmap.md` | `planning/roadmap.md` | Copy over as the starting state of the product roadmap. The research roadmap stays — it's a separate axis. |
| `architecture/<slug>/` | `planning/rfcs/<slug>/` or `planning/decisions/<slug>.md` | Architectural proposals that got built become ADRs; those still up for review become RFCs. |
| `systems/<slug>/` | `platform/systems/<slug>/` | Direct rename once the system is being built. The wiki page content carries over; engineering-ops adds the "surface area" and "known limitations" sections. |
| `evaluation/<slug>/` | *(no direct counterpart)* | Keep as-is; evaluation plans outlive the transition. Link from the matching `platform/systems/` page. |

## What doesn't change

- `raw/` — sources stay sources
- `wiki/` — compounding knowledge tree stays as-is
- `.open-questions/` — cross-cutting questions don't respect phase boundaries
- `index.md` — extends to cover the new sections, but existing sections stay

## A concrete example

Imagine a project called `aurora` is scaffolded as `research-project`. After eight months it has:

- `research/hypotheses/local-learning-stable.md` — "local Hebbian updates remain stable at scale with modulation"
- `research/experiments/hebbian-stability/` — experiment that *supported* the hypothesis
- `architecture/microfield-protocol.md` — proposed design
- `systems/hippocampal-index.md` — planned subsystem
- `evaluation/continual-learning-benchmark.md` — how to evaluate it

When the team starts building a runnable seed, they run `/memex:init-profile engineering-ops`. Result:

- `systems/hippocampal-index.md` \u2192 `platform/systems/hippocampal-index/README.md` (migrated). The old file is left with a redirect note.
- `architecture/microfield-protocol.md` stays in `architecture/`. When the RFC is formalised for review, a new `planning/rfcs/microfield-protocol/README.md` is written linking back to the original architecture doc.
- `research/hypotheses/local-learning-stable.md` stays where it is. Its `status:` becomes `active` (supported). New hypotheses still land here.
- `research/experiments/hebbian-stability/` archives to `.research/04072026-1200/hebbian-stability/` once the system is live and the experiment is complete; a redirect stub is left.
- A new `runbooks/hippocampal-index/README.md` is written the first time the new system pages someone.
- A new `planning/decisions/0001-adopt-jepa-style-predictor.md` captures the first architectural ADR.

Both trees coexist. The research history is preserved; the engineering reality gets its own home.
