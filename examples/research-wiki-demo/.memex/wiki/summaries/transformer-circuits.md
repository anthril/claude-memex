---
title: "Transformer Circuits: A Primer"
slug: transformer-circuits
type: summary
status: active
owner: demo
created: 2026-04-23
updated: 2026-04-23
---

# Transformer Circuits: A Primer

## Source

`raw/articles/transformer-circuits.md` — a fictional composite for the research-wiki demo. Not a real publication.

## TL;DR

A framework from Anthropic's interpretability team for reverse-engineering transformer behaviour into small, human-understandable "circuits" — specific patterns of attention heads and MLP neurons. The canonical example is the *induction head*, which explains in-context learning.

## Key claims

- **Induction heads** emerge during training and are responsible for in-context learning; early-layer attention heads locate prior occurrences of the current token, later layers copy what followed. See [[induction-heads]].
- **Mechanistic interpretability** ([[mechanistic-interpretability]]) aims for complete understanding of specific parameters, not statistical correlations — distinguishing it from saliency maps and probing classifiers.
- **Anthropic**'s interpretability team ([[anthropic]]), founded by Chris Olah in 2021, has published a series of papers demonstrating circuit analysis on small models.

## Entities and concepts mentioned

- [[anthropic]] — the organisation publishing this research
- [[mechanistic-interpretability]] — the methodological framework
- [[induction-heads]] — the canonical discovered circuit

## Connections to existing pages

This is the first source in the demo wiki. It establishes the initial page set for entities and concepts.

## Open questions raised

- `.open-questions/how-does-induction-work-at-scale.md` — does induction-head formation persist at 100B+ params?
- Can mechanistic interpretability findings transfer between model families, or does each architecture need its own circuit catalogue? *(filed inline on [[mechanistic-interpretability]])*

## Further reading

- Anthropic's "Transformer Circuits Thread" on transformer-circuits.pub
- Olah et al., "In-context Learning and Induction Heads" (2022)
