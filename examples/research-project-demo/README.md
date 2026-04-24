# research-project demo

A worked example of the `research-project` profile — scaffolded for a speculative AI-architecture project in its planning phase, modelled on real-world projects like `aurora` (a neuroscience-first AI paradigm proposal).

## What this demo shows

- How a **planning-phase** project uses the research-project wiki — hypotheses, methodology, literature review, architecture proposals, planned systems, evaluation plans
- How research sources flow from `raw/` \u2192 `wiki/summaries/` \u2192 `wiki/syntheses/` alongside the first-class `research/` artefacts
- How the project would transition into active development via `.rules/research-to-development.md`

## Scaffold

Run from a fresh project directory:

```bash
/memex:init research-project
```

Resulting tree:

```
.memex/
\u251c\u2500\u2500 README.md  AGENTS.md  index.md  log.md
\u251c\u2500\u2500 .open-questions/  .rules/  .state/
\u251c\u2500\u2500 raw/
\u2502   \u251c\u2500\u2500 articles/ papers/ books/ transcripts/ videos/
\u2502   \u2514\u2500\u2500 interviews/ standards/ datasets/ notes/ assets/
\u251c\u2500\u2500 wiki/
\u2502   \u2514\u2500\u2500 entities/ concepts/ summaries/ analyses/ syntheses/
\u251c\u2500\u2500 research/
\u2502   \u251c\u2500\u2500 hypotheses/ literature-review/ methodology/
\u2502   \u251c\u2500\u2500 experiments/ prompts/
\u2502   \u2514\u2500\u2500 roadmap.md
\u251c\u2500\u2500 architecture/
\u251c\u2500\u2500 systems/
\u2514\u2500\u2500 evaluation/
```

## A typical early-phase session

1. **Ingest a paper** on predictive coding:
   ```
   /memex:ingest .memex/raw/papers/friston-free-energy-2010.pdf
   ```
   Produces `wiki/summaries/friston-free-energy-2010.md`, extracts Karl Friston as an entity, creates `wiki/concepts/free-energy-principle.md`.

2. **State a hypothesis** linked to that concept:
   - `research/hypotheses/predictive-coding-scales.md` — "a hierarchical predictive-coding architecture will match transformer quality on language tasks with 10\u00d7 less compute, given event-driven activation."

3. **Propose an architecture** that would test it:
   - `architecture/microfield-protocol/README.md` — "microfield" design proposal linking the free-energy concept to a concrete computational unit

4. **Plan the experiments**:
   - `research/experiments/hebbian-stability/README.md` — testing local-learning stability
   - `research/experiments/sparse-activation-efficiency/README.md` — testing energy scaling

5. **Draft evaluation**:
   - `evaluation/continual-learning-benchmark/README.md` — adapted from Nature's catastrophic-forgetting benchmark suite

6. **Ask the wiki a question**:
   ```
   /memex:query "what does the wiki say about why sparse activation helps memory efficiency?"
   ```
   Pulls from `wiki/concepts/free-energy-principle.md`, `wiki/summaries/friston-free-energy-2010.md`, and any relevant entities. Offers to file the answer back as `wiki/analyses/why-sparse-helps-memory.md`.

## Transitioning into development

When the project reaches the "time to build" stage (runnable prototype, deployment target, tests, first user), run:

```
/memex:init-profile engineering-ops
```

The profile-builder skill detects the existing `research-project` scaffold and proposes an **overlay** \u2014 engineering-ops surfaces added alongside the research tree. See [`.memex/.rules/research-to-development.md`](../../templates/profiles/research-project/.memex/.rules/research-to-development.md) for the full graduation map.

## See also

- [`templates/profiles/research-project/`](../../templates/profiles/research-project/) \u2014 the profile source
- [`examples/research-wiki-demo/`](../research-wiki-demo/) \u2014 the pure research-wiki walkthrough
- [`examples/custom-profile-demo/WALKTHROUGH.md`](../custom-profile-demo/WALKTHROUGH.md) \u2014 building a custom profile from scratch
