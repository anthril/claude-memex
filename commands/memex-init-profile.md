---
description: Interactively build a custom Memex profile tailored to this project's folder shape
argument-hint: "[base-profile]"
allowed-tools: Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# /memex:init-profile

Interactive alternative to `/memex:init`. Use this when none of the six built-in profiles (`engineering-ops`, `research-wiki`, `research-project`, `book-companion`, `personal-journal`, `generic`) cleanly fits the project's actual shape.

Delegates to the [`profile-builder`](../skills/profile-builder/SKILL.md) skill, which:

1. Surveys the current project with Glob/Grep to infer what it is
2. Picks the closest built-in profile as a starting point (or uses `[base-profile]` if given)
3. Interviews the user with targeted questions about taxonomy and gating
4. Drafts `allowedTopLevel`, `readmeRequired`, `frontmatter.enum.type`, `index.sections`
5. Writes `memex.config.json`, the `.memex/` tree, `CLAUDE.md`, `AGENTS.md`, `README.md`, `index.md`, `log.md`, `.rules/README.md`, `.open-questions/README.md`

## Usage

```
/memex:init-profile                   # survey + interview from scratch
/memex:init-profile engineering-ops   # fork engineering-ops and customise
/memex:init-profile research-project  # fork research-project and customise
```

## Safety

- Refuses to run if `.memex/` or `memex.config.json` already exists in the project root — same guard as `/memex:init`.
- Will not overwrite any pre-existing file. If the interview would produce a file that already exists, the skill stops and asks the user.
- Does not modify anything in the plugin repo itself. The generated profile lives only in the current project unless the user explicitly asks to contribute it back.

## After scaffold

Same three next-steps summary as `/memex:init`:

1. Review `.memex/AGENTS.md` — adjust the `owner:` frontmatter
2. Review `memex.config.json#/codeToDocMapping` — empty by default; add project-specific mappings
3. Run `/memex:log` to confirm hooks are wired up

## See also

- [`/memex:init`](memex-init.md) — if one of the built-in profiles fits
- [`docs/profile-authoring.md`](../docs/profile-authoring.md) — hand-author a profile instead
