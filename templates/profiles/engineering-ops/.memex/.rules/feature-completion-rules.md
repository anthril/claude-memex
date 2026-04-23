---
title: Feature completion rules
slug: feature-completion-rules
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Feature completion rules

What "done" means for a feature or system, for both the code and the wiki.

## 1. Feature README structure

Every `platform/features/<slug>/README.md` should cover, at minimum:

```markdown
# {{Feature name}}

## What it does
One-paragraph summary for someone unfamiliar with the feature.

## Where it lives
- Entry points: file paths / routes
- Primary systems: links to `platform/systems/<slug>/README.md`
- Related entities: links to `entities/<slug>/README.md`

## Flows
Numbered user / system flows with the critical decision points.

## Surface area
APIs, events, database tables, third-party integrations.

## Known limitations
What it does NOT handle, deliberately.

## Open questions
Linked from or scoped to this feature.

## Changelog
Major changes with dates.
```

## 2. Code-to-doc mapping

If `memex.config.json#/codeToDocMapping` is configured, the `doc-required.py` hook enforces that new code under a tracked path has a matching doc. Typical mappings for an `engineering-ops` project:

```json
{
  "codePattern": "src/app/features/*/",
  "requiresDoc": "platform/features/{1}/README.md",
  "severity": "warn-then-block"
}
```

Expand with project-specific routes. Leave the default empty until you have real paths to track.

## 3. Definition of done

A feature is NOT done until:
1. The README exists with all frontmatter fields
2. Referenced entities / systems / workflows have their own pages (or explicit `*not-yet-documented*` markers with open questions)
3. The index has the feature listed under `## Features`
4. The log has an `activate` entry for the feature
5. All inline TODOs in the feature's code have been promoted to `.open-questions/` or scoped sections
