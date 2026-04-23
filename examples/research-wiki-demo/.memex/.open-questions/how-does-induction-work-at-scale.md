---
title: Does induction-head formation persist at frontier scale?
slug: how-does-induction-work-at-scale
type: open-question
status: open
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

## Context

Raised by [[transformer-circuits]] during ingest on 2026-04-23. The article notes that current circuit-analysis results only cover models up to ~1B parameters. Whether the same mechanism (two-stage induction head) persists at 100B+ params is load-bearing for the safety story that [[mechanistic-interpretability]] promises.

## The question

Do induction heads — as defined in the two-stage early/late attention pattern — continue to implement in-context learning at frontier model scale? Or do larger models develop different, possibly non-circuit-level, mechanisms for the same capability?

## What we know

- Olah et al. demonstrated the pattern in 2L and 3L attention-only transformers
- The mechanism was shown to emerge during training at a specific phase transition
- No published mechanistic study has confirmed the same circuit in >10B param models (as of the source article's implied timeframe)

## What we'd need to decide

- Would a confirmatory study on an open-weights mid-scale model (e.g. Llama-70B) settle it?
- Is it even well-posed to look for "the same" circuit at different scales, given polysemanticity / superposition effects?

## Proposed resolutions

1. **Ingest a later paper** covering >10B-param circuit analysis if one exists — promote findings into this page
2. **Leave open** — this is genuinely an empirical question the field hasn't answered; tracking it here is valuable
