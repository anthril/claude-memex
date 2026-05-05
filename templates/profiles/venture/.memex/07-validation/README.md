---
title: 07 — Validation
slug: phase-validation
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 07 — Validation

Where we record every pivot and refine decision so the customer-development
loop is auditable. Not a phase that "happens once" — it gets entries every
time the venture changes course.

Curriculum source: COMP1100 Ch. 1, *verify / pivot / refine*.

## Required artifacts

| File | Skill |
|---|---|
| `pivot-refine-log.md` | `venture-core/pivot-refine-log` (append-only) |

## Pivot vs refine

See [`../.rules/pivot-refine-rules.md`](../.rules/pivot-refine-rules.md)
for the distinction and the required entry shape.

In short:

- **Pivot**: change a core element of the model, keep another. Bumps the
  BMC version.
- **Refine**: tweak the same model. Doesn't necessarily bump the BMC, but
  is still logged.

## Don't throw away learning

Every pivot/refine entry calls out *what was kept*, not just what changed.
The whole point of the customer-development loop is that you never start
over from zero — you compound the learning.

## What this enables

- `phase-router` reads this log to decide whether the venture is in a
  stable phase (focused execution) or an unstable one (more discovery
  needed). Three pivots in a quarter is a slow-down signal.
- `venture-handoff-doc` summarises the pivot/refine history so a new team
  member can see the journey.
