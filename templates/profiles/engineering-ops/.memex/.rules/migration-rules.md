---
title: Migration rules
slug: migration-rules
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Migration rules

How schema changes, database migrations, and security-relevant operations get documented.

## 1. Every migration needs a linked doc

Configure `memex.config.json#/codeToDocMapping` with an entry like:

```json
{
  "codePattern": "supabase/migrations/*.sql",
  "requiresDoc": "ANY .md containing the slug OR header comment `-- Doc: .memex/<path>.md`",
  "severity": "block"
}
```

The `ingest-doc-link.py` hook enforces this. A new migration is blocked unless either:

- The migration's filename or derived slug is referenced from any `.memex/` markdown file, OR
- The migration file itself contains a header comment: `-- Doc: .memex/platform/systems/users/README.md`

## 2. Security-relevant changes require an audit entry

When the change touches authentication, authorisation, PII handling, or data export, create a corresponding audit folder:

```
.audits/DDMMYYYY-HHMM/README.md
```

The README must carry the standard frontmatter plus a summary section describing:
1. What changed (the code surface)
2. What was at risk before
3. What's protected now
4. How it was tested

## 3. Data migrations vs. schema migrations

| Kind | Location | Doc target |
|---|---|---|
| Schema change (`ALTER TABLE`, new column) | Normal migration file | Linked entity or system README |
| Data backfill | Separate backfill script | `.research/<timestamp>/backfill.md` describing the rationale, sample data, and rollback |
| Security patch | Migration + audit | Linked system README AND `.audits/<timestamp>/README.md` |
