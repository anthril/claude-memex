---
title: Pivot vs refine rules (Ch. 1)
slug: pivot-refine-rules
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Pivot vs refine rules

Curriculum source: COMP1100/COMP7110 Ch. 1, *Introduction to Innovation*.
This rule is **not blocking**, but every pivot or refine **must** be logged
in `07-validation/pivot-refine-log.md` with the structure below. The Stop
hook surfaces missing entries.

## Pivot vs refine

- **Pivot**: change one core element of the model, keep another. Example:
  same problem, different segment. Same segment, different value prop. Same
  product, different channel.
- **Refine**: tweak the same model. Same problem, segment, value prop and
  channel — but a sharper messaging, a smaller scope, a different price
  point.

In both cases, *keep what was learned*. Never throw away the prior
hypothesis register, BMC, or VPC. Set their status to `superseded` and link
to the new versions.

## Required log entry shape

```markdown
## [YYYY-MM-DD] <pivot|refine> | <one-line summary>

### Trigger evidence
What happened that caused this. Link to interviews, learning cards,
metrics, or external events.

### Decision
Pivot or refine? What we are now doing differently.

### What changed
Cells / pages / hypotheses / VPC sections that were updated. Use markdown
links, not bare paths.

### What was kept
Explicitly call out the parts of the model that survive. This is the
"don't throw away learning" rule.

### New version pointers
- BMC: link to the new version
- VPC(s): link to the new version(s)
- Hypothesis register: list of hypothesis IDs whose status changed
```

## Frequency

Don't pivot every week. The decision should be backed by *enough*
evidence — typically a learning card with a clear refutation, or a pattern
across ≥ 3 interviews in the same segment. Refines are cheaper and can
happen more often.

## When in doubt

If you can't tell whether something is a pivot or a refine, it's almost
certainly a refine. A pivot is structural — a different segment, a
different revenue model, a different channel. If the change fits inside
the existing BMC cells without bumping the version, it's a refine.

## Cross-references

- The Stop hook checks that any week with hypothesis-status changes also
  has a `pivot-refine-log.md` entry.
- The `phase-router` skill reads this log to decide whether the venture is
  in a stable phase or an unstable one. Three pivots in a quarter is a
  signal to slow down on solution work and revisit problem discovery.
