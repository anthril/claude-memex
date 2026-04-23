---
title: Documentation rules
slug: documentation-rules
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Documentation rules

Hook-enforced. Blocked writes will explain which section was violated.

## 1. Top-level structure

Writes under `.memex/` must target one of the top-level entries declared in `memex.config.json#/allowedTopLevel`. The default set for the `engineering-ops` profile:

```
README.md  AGENTS.md  index.md  log.md
.audits/  .research/  .open-questions/  .rules/  .state/
entities/  platform/{features,systems}/  workers/  workflows/  agents/
```

To add a new top-level slot: edit `memex.config.json`, get the change reviewed, and file a corresponding entry in `.open-questions/` explaining why.

## 2. Dated folders

`.audits/` and `.research/` require child folders named in the format `DDMMYYYY-HHMM` (e.g. `23042026-1430`). No colons, no spaces, no timezone suffix. This keeps the names valid on Windows NTFS and sorts chronologically under a stable locale.

## 3. Frontmatter

Every `README.md` and `AGENTS.md` under `.memex/` must begin with a YAML frontmatter block:

```yaml
---
title: Human-readable title
slug: kebab-case-identifier
type: feature|system|entity|worker|agent|workflow|open-question|rule
status: draft|active|deprecated
owner: person-or-team
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Missing or incomplete frontmatter → `PostToolUse` block. Fix and retry.

## 4. Naming

- Folders: kebab-case (`my-entity`, not `MyEntity` or `my_entity`)
- Files: kebab-case with optional `01-` ordering prefix (`01-data-model.md`)
- Exceptions: `README.md`, `AGENTS.md`, `CHANGELOG.md`, `CONVENTIONS.md`, `.resolved`

## 5. README-required trees

Before any file can be written into a new `entities/<slug>/`, `platform/features/<slug>/`, `platform/systems/<slug>/`, `workers/<slug>/`, `agents/<slug>/`, or `workflows/<slug>/` folder, the first write MUST be `README.md` in that folder. The hook will block any other first write with the error `has no README.md`.

## 6. `updated:` discipline

Every edit to a page must bump the `updated:` frontmatter field. The `Stop` hook flags pages whose referenced code was touched without an `updated:` bump; these surface as stale-check warnings.

## 7. No inline TODOs

`TODO`, `TBD`, `XXX`, `FIXME` markers in prose are promoted. Cross-cutting → `.open-questions/<slug>.md`. Scoped → a `## Open questions` section on the owning page. The `Stop` hook watches for inline markers and prompts Claude to promote them.
