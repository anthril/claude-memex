---
title: Open questions
slug: open-questions
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-27
---

# Open questions

Cross-cutting unresolved items. One file per question (`<slug>.md`). Resolved questions move to `.resolved/` with a dated resolution note appended.

## File template

```markdown
---
title: Question title
slug: kebab-case-slug
type: open-question
status: open
owner: unassigned
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

## Context
What prompted the question. Link the page / audit / session where it surfaced.

## The question
One or two sentences. Crisp.

## Related files
Markdown links to every file the question touches — runbooks, specs, code, configs, ADRs.
Use `[label](relative/path)`; bare paths do not count.

- [<short label>](<relative/path/to/file>) — <one-line why this file is relevant>
- ...

## What we know
Dot points. Include links to related pages.

## What we'd need to decide
Dot points on the decision criteria or blockers.

## Proposed resolutions
Numbered alternatives with tradeoffs, if any.
```

The `## Related files` section is **mandatory**. The wiki-lint skill flags open questions whose `## Related files` is missing, empty, or contains bare paths instead of markdown links. Engineering questions almost always touch a runbook, an ADR, or a service config — name them. If a question genuinely touches nothing, it probably belongs as an inline note on the most-affected page rather than as a cross-cutting open question.

## Workflow

- Add via `/memex:open-q <title>` (shipped by the plugin)
- Triage periodically via the `open-questions-triage` skill — it groups by age and proposes promotions / resolutions
- When resolved, move the file to `.resolved/<slug>.md` and append a `## Resolution` section with the date and what was decided
