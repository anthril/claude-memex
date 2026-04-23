---
title: Induction heads
slug: induction-heads
type: concept
status: active
owner: demo
created: 2026-04-23
updated: 2026-04-23
---

# Induction heads

## What they are

A specific attention-head pattern that emerges during transformer training and implements **in-context learning** — the ability to continue a pattern seen earlier in the context window.

## How they work (two-step)

1. **Early-layer attention heads** look at the current token and find prior occurrences of the same token in the context
2. **Later-layer attention heads** use that signal to attend to the token that *followed* the prior occurrence, and copy it as the prediction

This gives the model `[A][B]...[A] → predict [B]` behaviour without gradient updates.

## Why they matter

- They are the canonical demonstration that transformer behaviour can be reverse-engineered into named, understood circuits
- Their emergence is tied to the "phase transition" in in-context learning capability during training
- Part of [[anthropic]]'s interpretability team's published work under the [[mechanistic-interpretability]] programme

## Open questions

See `.open-questions/how-does-induction-work-at-scale.md` — whether this mechanism persists at frontier scale, or whether larger models develop different implementations of the same capability.

## First encountered

[[transformer-circuits]] ingested 2026-04-23. Reference: Olah et al., "In-context Learning and Induction Heads" (2022).
