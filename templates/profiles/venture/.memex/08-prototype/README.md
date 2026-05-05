---
title: 08 — Prototype
slug: phase-prototype
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 08 — Prototype

Paper prototypes, digital prototypes, feedback. The cheap part of
"learning whether the solution works in concept" — distinct from the MVP
phase, which tests whether real users adopt.

Curriculum source: COMP1100 Week 7 studio, *Prototyping*.

## Sub-folder structure

```
08-prototype/
├── paper/
│   └── <slug>.md
├── digital/
│   └── <slug>/README.md       (required — readme-required hook)
└── feedback/
    └── <slug>.md
```

## Required artifacts

| File | Skill |
|---|---|
| `paper/<slug>.md` | `prototyping/paper-prototype` |
| `digital/<slug>/README.md` | `prototyping/digital-prototype` (delegates to `prototyping/figma-design-handoff`) |
| `feedback/<slug>.md` | `prototyping/prototype-feedback-collect` |

## Divergent → convergent

The flow: `divergent-ideate` (open up; lots of options; no critique) →
`converge-ideas` (narrow to 1–3 finalists) → paper prototype → feedback →
maybe digital prototype → more feedback. The prototype tree is a record
of *what was tried*, not just *what won*.

## Paper before pixels

The studio rule: test the concept on paper before you build pixels. Cheap
to be wrong on paper. Painful to be wrong in Figma. The
`paper-prototype` skill insists on this for new concepts.

## Figma handoff

`digital-prototype` calls `figma-design-handoff` to pull metadata from a
Figma file (read-only by default — see
[`shared/reference/connector-confirmation.md`](../../../shared/reference/connector-confirmation.md)
for the mutation gate). Outputs a Figma URL, screenshot snapshots, design
tokens for export, and a code-connect map proposal.

## The blocking gate

`prototype-vs-mvp-distinguish` (see
[`../.rules/prototype-vs-mvp-rules.md`](../.rules/prototype-vs-mvp-rules.md))
refuses to label any artifact in this folder as an MVP. MVPs go under
`09-mvp/`.
