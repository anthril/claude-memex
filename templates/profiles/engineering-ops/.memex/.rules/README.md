---
title: Rules (engineering-ops)
slug: rules-index
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Rules

Rules that govern writes into `.memex/`. These are read by Claude at session start (via the `SessionStart` hook) and enforced by the `PreToolUse` / `PostToolUse` hooks.

## Files

| File | Purpose |
|---|---|
| [documentation-rules.md](documentation-rules.md) | Path, naming, frontmatter, dated folders |
| [planning-rules.md](planning-rules.md) | PRD vs RFC vs ADR — when each applies, required shape, decision lifecycle |
| [feature-completion-rules.md](feature-completion-rules.md) | What "done" means for a feature or system |
| [migration-rules.md](migration-rules.md) | How database migrations and schema changes get documented |
| [incident-rules.md](incident-rules.md) | Blameless postmortem structure, timing, action-item discipline |
| [runbook-rules.md](runbook-rules.md) | On-call runbook skeleton: trigger \u2192 symptom \u2192 diagnosis \u2192 remediation \u2192 escalation |

## Changing a rule

If a rule is wrong or too strict, file an entry under `.open-questions/` with the proposed change and rationale. Do not edit `memex.config.json` or these rule files without filing one first.
