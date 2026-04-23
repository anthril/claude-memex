---
description: Promote a raw / research / analysis snippet to a permanent wiki page
argument-hint: "<doc-path> <target-type>"
allowed-tools: Read, Write, Edit, Grep, Bash
---

# /memex:promote

Promote a transient document (under `.research/`, `raw/`, `wiki/analyses/`, or anywhere non-canonical) to a permanent wiki page under the correct taxonomy slot.

## Usage

```
/memex:promote .memex/.research/23042026-1000/oauth-findings.md entity
/memex:promote .memex/wiki/analyses/billing-comparison.md concept
/memex:promote .memex/raw/articles/foo.md summary
```

## Target types

Map the target type to the profile's target folder. For `engineering-ops`:

| target-type | Path |
|---|---|
| `entity` | `entities/<slug>/README.md` |
| `feature` | `platform/features/<slug>/README.md` |
| `system` | `platform/systems/<slug>/README.md` |
| `worker` | `workers/<slug>/README.md` |
| `agent` | `agents/<slug>/README.md` |
| `workflow` | `workflows/<slug>/README.md` |

For `research-wiki`:

| target-type | Path |
|---|---|
| `entity` | `wiki/entities/<slug>.md` |
| `concept` | `wiki/concepts/<slug>.md` |
| `summary` | `wiki/summaries/<slug>.md` |
| `analysis` | `wiki/analyses/<slug>.md` |
| `synthesis` | `wiki/syntheses/<slug>.md` |

## Behaviour

1. Read the source doc
2. Propose a kebab-case slug from the title. Ask the user to confirm or rename.
3. Create the target doc with full frontmatter — inherit where sensible, but `type:` is set to the target type, `status: active`, `created:` today, `updated:` today
4. Copy the body, adapting structure to the target type's template:
   - **entity/feature/system/etc.** — expected body: `## What it is / ## Where it lives / ## Surface area / ## Open questions / ## Changelog`
   - **summary/analysis/synthesis** — existing body usually fits as-is
5. Leave the source doc in place BUT prepend a line:

   ```markdown
   > **Promoted** to [`<new-path>`](<relative-path>) on YYYY-MM-DD.
   ```

   (Don't delete the source — keep the provenance.)
6. Update `index.md` with the new entry under the appropriate section
7. Find and update all references to the source doc (optional — prompt the user: "Update `<n>` referring pages to point at the promoted page?")
8. Append `log.md` with `event: promote | <old-slug> → <new-slug>`

## Guardrails

- Refuse if the target path already exists — ask the user whether to merge or rename
- Refuse if the source doc has no recognisable body (too thin to promote)
- Don't auto-delete the source even if the user asks — keep the provenance trail
