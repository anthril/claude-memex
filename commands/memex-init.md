---
description: Scaffold a Memex wiki into the current project
argument-hint: "[profile]"
allowed-tools: Read, Write, Bash, Glob
---

# /memex:init

Scaffold `.memex/`, `memex.config.json`, and a `CLAUDE.md` reference into the current project. Refuses to overwrite existing files.

## Usage

```
/memex:init [profile]
```

- `profile` (optional, default `generic`) — one of: `engineering-ops`, `research-wiki`, `research-project`, `book-companion`, `personal-journal`, `generic`

If none of the built-in profiles fits, use [`/memex:init-profile`](memex-init-profile.md) — the profile-builder skill surveys your project and generates a tailored custom profile.

## What the command does

Before generating anything, check whether `.memex/` or `memex.config.json` already exist. If either exists, do NOT overwrite — instead:
1. List what would have been created under each (file paths + one-line descriptions)
2. List what is already present (so the user can compare)
3. Stop. Ask the user how to proceed (add only missing files, overwrite, cancel).

If nothing exists, copy the selected profile's template tree into the current working directory. The template lives at `${CLAUDE_PLUGIN_ROOT}/templates/profiles/<profile>/`. Every file in that tree maps 1:1 to a path in the target project:

- `${CLAUDE_PLUGIN_ROOT}/templates/profiles/<profile>/memex.config.json` → `./memex.config.json`
- `${CLAUDE_PLUGIN_ROOT}/templates/profiles/<profile>/.memex/**` → `./.memex/**`
- `${CLAUDE_PLUGIN_ROOT}/templates/profiles/<profile>/CLAUDE.md` → merge into `./CLAUDE.md`:
  - If `./CLAUDE.md` does not exist, write it out
  - If it does exist, print the template content and ask the user to splice it in manually (never silently overwrite)

Drop any `.keep` files during copy — they exist only to preserve empty directories in git.

Do placeholder substitution on files that contain `{{ProjectName}}`. Infer the project name from the current folder name, but ask the user to confirm before substituting.

## After copy

Print a summary:

1. Files created (paths)
2. Files skipped (paths + reason)
3. The next 3 actions the user should take:
   - Review `.memex/AGENTS.md` and adjust `owner:` frontmatter
   - Review `memex.config.json#/codeToDocMapping` — empty by default; add mappings relevant to this codebase
   - Run `/memex:log` to confirm the hook layer is wired up correctly
4. A link to `docs/concepts.md` and `docs/README.md` in the plugin repo

## Profiles

| Profile | Shape |
|---|---|
| `engineering-ops` | `planning/{prds,rfcs,decisions,roadmap.md}`, `entities/`, `platform/{features,systems,integrations}/`, `workers/`, `agents/`, `workflows/`, `runbooks/`, `processes/`, `environments/`, `.audits/`, `.incidents/`, `.research/` |
| `research-wiki` | `raw/{articles,papers,books,transcripts,videos,interviews,standards,datasets,notes,assets}/`, `wiki/{entities,concepts,summaries,analyses,syntheses}/` |
| `research-project` | All of `research-wiki` plus `research/{hypotheses,literature-review,methodology,experiments,prompts,roadmap.md}`, `architecture/`, `systems/`, `evaluation/` |
| `book-companion` | `raw/chapters/`, `wiki/{characters,places,themes,plot-threads}/`, `timeline.md` |
| `personal-journal` | `raw/entries/`, `wiki/{topics,goals,reflections}/` |
| `generic` | `topics/`, `index.md`, `log.md`, `.open-questions/` |

All profiles share `AGENTS.md`, `README.md`, `index.md`, `log.md`, `.open-questions/`, `.state/`.
