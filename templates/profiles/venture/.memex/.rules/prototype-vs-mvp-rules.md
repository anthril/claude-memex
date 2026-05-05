---
title: Prototype vs MVP rules (Ch. 6)
slug: prototype-vs-mvp-rules
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Prototype vs MVP rules

Curriculum source: COMP1100/COMP7110 Ch. 6, *Minimum Viable Product*. The
`prototype-vs-mvp-distinguish` skill enforces this rule. Override with
`--force`; override is logged automatically.

## The five-dimension distinction

| Dimension | Prototype | MVP |
|---|---|---|
| **Audience** | Internal team, design partners, ≤ 5 friendlies | Real prospects from the early-adopter segment |
| **Fidelity** | Low to medium — paper, click-through, fake-door | Production-quality on the slice you ship |
| **Scope** | One feature, one flow, one open question | The smallest end-to-end thing that lets you test the *primary* hypothesis |
| **Environment** | Sandboxed; canned data; no auth or simulated auth | Live; real data; real auth; real billing if billing is in the hypothesis |
| **What it proves** | The solution is technically possible / desirable in concept | Real users will adopt this end to end given the constraints they have |

If an artifact fails the MVP test on **any** of these five dimensions, it's
a prototype. Do not call it an MVP.

## The blocking check

`prototype-vs-mvp-distinguish` reads the artifact's frontmatter and any
linked spec. It refuses to set `type: mvp-spec` if any of:

- The audience is not the segment's early adopters
- Fidelity is not production on the shipped slice
- Scope is wider than the primary hypothesis (KISS rule)
- The environment is sandboxed
- The artifact does not state which hypothesis it tests with what threshold

The first time this check fires, the user usually sets `--force`. That's
fine — but the override is logged, and `phase-router` will keep nagging
until either the artifact is converted to a real MVP or its label is
changed back to prototype.

## Why this matters

The Ries point: an MVP is for learning whether real users adopt. A
prototype is for learning whether the solution is feasible or desirable in
concept. Mislabeling a prototype as an MVP causes the team to optimise for
the wrong feedback (looks-pretty vs do-they-pay), and to draw conclusions
the artifact doesn't support.

## Types of MVP

The Ch. 6 menu (selected by `mvp-type-select`):

| Type | What it tests | Example |
|---|---|---|
| **Pre-order** | Will they pay? | Buy-now button → "Sorry, sold out — join the waitlist" → measure intent-to-pay |
| **Audience-building** | Are they engaged? | Newsletter or content drip; measure subscribe-then-open rate |
| **Show-and-tell** | Do they want it? | Demo video, landing page; measure sign-up rate |
| **Partial product** | Will they use a thin slice? | Real product but only one feature working end-to-end |

Each of these is genuinely an MVP if it satisfies the five-dimension test
above. A landing page with no commitment ask is a prototype, not an MVP.
