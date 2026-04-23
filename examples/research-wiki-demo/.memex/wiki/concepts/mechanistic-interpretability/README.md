---
title: Mechanistic interpretability
slug: mechanistic-interpretability
type: concept
status: active
owner: demo
created: 2026-04-23
updated: 2026-04-23
---

# Mechanistic interpretability

## What it is

A research methodology that aims for **complete, parameter-level understanding** of what a neural network computes — not just statistical correlations or post-hoc explanations, but reverse-engineering specific attention heads, MLP neurons, and their circuits.

## Contrast with other approaches

| Approach | Goal | Typical output |
|---|---|---|
| **Mechanistic interpretability** | Complete understanding of specific parameters | Human-readable circuit descriptions |
| Saliency maps | Highlight which inputs matter | Per-input attribution scores |
| Probing classifiers | Find linear structure in activations | Statistical accuracy numbers |

The claim is that only mechanistic understanding scales to a useful safety story — you cannot "surgically remove" a capability without knowing how it's implemented.

## Key findings so far

- [[induction-heads]] — the canonical discovered circuit; explains in-context learning
- Superposition — models represent more features than they have neurons by packing them into non-orthogonal directions (not yet covered in this wiki; candidate for next ingest)

## Open questions

- Does mechanistic understanding transfer between model families (Llama vs GPT vs Claude), or must each architecture be re-analysed from scratch? *(raised by [[transformer-circuits]])*
- At what scale does circuit-level analysis stop being tractable? Current demonstrations are <1B params.

## First encountered

[[transformer-circuits]] ingested 2026-04-23.
