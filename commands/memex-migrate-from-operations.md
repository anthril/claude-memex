---
description: Migrate a Lumioh-style .operations/ tree to .memex/
argument-hint: "[--dry-run]"
allowed-tools: Read, Write, Edit, Glob, Bash
---

# /memex:migrate-from-operations

One-shot helper for projects that already use a Lumioh-style `.operations/` tree and want to adopt Memex without losing content.

## Usage

```
/memex:migrate-from-operations            # actually migrate
/memex:migrate-from-operations --dry-run  # print the plan only
```

The mechanical work is done by [`scripts/migrate_from_operations.py`](../scripts/migrate_from_operations.py) — a tested Python script the command shells out to. See `tests/test_migration.py` for coverage.

## Behaviour

1. Locate `.operations/` at the project root. Refuse if it's absent or if `.memex/` already exists (we won't overwrite).
2. **Verify the shape.** The `.operations/` tree should contain: `AGENTS.md`, `README.md`, `.rules/`, `entities/`, `platform/features/`, `platform/systems/`, and similar engineering-ops folders. If the shape is unfamiliar, print the folder list and stop — ask the user.
3. **Propose the move.** Print a table of `<old-path> → <new-path>`. For `--dry-run`, stop here.
4. **Execute.** `git mv .operations .memex` (preserves history). If the repo is not a git repo, use a filesystem move with `os.rename`.
5. **Extract the schema to `memex.config.json`.** Read the rules referenced by the old hooks and produce a config that preserves them:

   ```json
   {
     "$schema": "https://raw.githubusercontent.com/anthril/claude-memex/main/schemas/memex.config.schema.json",
     "version": "1",
     "profile": "engineering-ops",
     "root": ".memex",
     "allowedTopLevel": ["README.md","AGENTS.md","index.md","log.md",".audits",".research",".open-questions",".rules","entities","platform","workers","workflows","agents"],
     "datedFolders": {"paths":[".audits",".research"], "format":"DDMMYYYY-HHMM"},
     "readmeRequired": ["entities/*","platform/features/*","platform/systems/*","workers/*","agents/*","workflows/*"],
     "frontmatter": { ... },
     "codeToDocMapping": [ ... ]
   }
   ```

   Copy the `codeToDocMapping` entries from the old `feature-doc-required.py` / `migration-doc-link.py` hooks (hard-coded patterns become config entries).

6. **Update in-tree references.** `Grep` for the string `.operations/` across the project; offer to replace with `.memex/` in each hit. Be careful with code comments that reference the old path deliberately (e.g. CHANGELOGs).
7. **Remove the old hooks.** If the project's `.claude/settings.json` points at `.claude/hooks/operations-*.py`, remove those entries — the plugin's hooks take over. Keep the old hook scripts themselves around until the user has verified the migration, then offer to delete.
8. **Append `log.md`.** `## [YYYY-MM-DD] migrate | .operations/ → .memex/`

## What we don't touch

- `.operations/CHANGELOG.md` entries — preserved verbatim with the folder rename
- The content of any page — only the surrounding path references
- `memex.config.json`'s `codeToDocMapping` beyond the patterns your old hooks enforced; add new ones yourself

## After migration

Run `/memex:lint` as the first action in the migrated project. It'll surface any dangling references missed in step 6.
