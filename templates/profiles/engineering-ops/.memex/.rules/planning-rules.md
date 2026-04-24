---
title: Planning rules
slug: planning-rules
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Planning rules

How the team records product intent, technical design, and decisions. The three artefact types are distinct — don't mix them.

## 1. PRD — Product Requirement Doc

**Purpose:** *why* and *what*, not *how*.

**Location:** `planning/prds/<slug>/README.md`

**When:** before any non-trivial feature. A one-paragraph Slack thread is fine for a button colour change; a PRD is required for anything that touches more than one system or changes user-visible behaviour.

**Required sections:**

```markdown
# {{Feature name}}

## Problem
Who is hurting, how much, and why today's state is unacceptable.

## Goal
One paragraph stating the outcome we want, measurable if possible.

## Non-goals
What we deliberately will NOT do. This is the most valuable section — it bounds scope.

## User stories
1. As a <role>, I want <outcome>, so that <benefit>.

## Success metrics
How we'll know it worked. Leading and lagging indicators.

## Risks and open questions
Link to `.open-questions/` entries.
```

## 2. RFC — Request For Comment

**Purpose:** *how*, proposed for review.

**Location:** `planning/rfcs/<slug>/README.md`

**When:** whenever the implementation approach isn't obvious, or more than one engineer will touch the surface, or the design crosses team boundaries.

**Required sections:**

```markdown
# {{Design name}}

## Context
What problem are we solving? Link the PRD.

## Proposal
The design in enough detail that a different engineer could implement it.

## Alternatives considered
At least two. Explain why they were rejected.

## Trade-offs
What we give up. What breaks. What becomes harder.

## Rollout plan
Feature flag? Phased? Big-bang? Rollback plan?

## Open questions
Things the reviewers need to resolve.
```

## 3. ADR — Architectural Decision Record

**Purpose:** the single-line answer to "why did we do it this way?", recorded permanently.

**Location:** `planning/decisions/<slug>.md`

**When:** whenever a decision is made that future engineers will wonder about. New library, new pattern, major refactor, architectural constraint adopted or dropped.

**Required structure — short, NUMBERED, immutable once accepted:**

```markdown
---
title: "ADR-{{NNNN}}: {{short decision name}}"
slug: adr-{{nnnn}}-{{kebab-slug}}
type: decision
status: proposed|accepted|superseded
owner: {{person}}
created: {{date}}
updated: {{date}}
---

# ADR-{{NNNN}}: {{Decision}}

## Status
proposed | accepted | superseded-by ADR-{{NNNN}}

## Context
Two paragraphs. What forces are at play?

## Decision
One paragraph. The actual decision.

## Consequences
Bullet list. What becomes easier, what becomes harder, what becomes impossible.
```

## 4. Decision lifecycle

- **proposed** — drafted, under review. Editable.
- **accepted** — ratified. **Immutable.** If you need to change the decision, write a new ADR that supersedes it and link both ways.
- **superseded** — replaced by a newer ADR. Keep the file; update `status:` to `superseded` and add `superseded-by: ADR-NNNN`.

Never delete an accepted ADR. The audit trail is the point.

## 5. Roadmap

`planning/roadmap.md` has no frontmatter requirement and no schema. Edit it freely. It's the single "what's next" page — keep it short, priority-ordered, and with a `last updated:` line at the top.
