# Authoring a profile

Profiles are pure data — a `memex.config.json` + a `.memex/` template tree + a `CLAUDE.md` stub. Memex ships six profiles (`engineering-ops`, `research-wiki`, `research-project`, `book-companion`, `personal-journal`, `generic`). You can add your own.

## Interactive path: `/memex:init-profile`

Before hand-authoring, consider running [`/memex:init-profile`](../commands/memex-init-profile.md) inside the target project. The [profile-builder skill](../skills/profile-builder/SKILL.md) surveys the project's existing folders, interviews you, and generates a tailored `memex.config.json` + `.memex/` tree in one session. See [`examples/custom-profile-demo/WALKTHROUGH.md`](../examples/custom-profile-demo/WALKTHROUGH.md) for a worked example.

The hand-authoring guide below is the right path if you want to contribute a reusable profile upstream (so others can pick it at `/memex:init <slug>` time).

## Anatomy of a profile

```
templates/profiles/<profile-name>/
├── memex.config.json                 # Schema
├── CLAUDE.md                         # Project-level Claude instructions
└── .memex/
    ├── AGENTS.md                     # Binding contract
    ├── README.md                     # Folder map
    ├── index.md                      # Catalogue stub
    ├── log.md                        # Ledger with `## [YYYY-MM-DD] init | ...` seed
    ├── .open-questions/README.md     # Template + instructions
    ├── .rules/README.md              # Rule index
    └── <profile-specific folders>/
        └── .keep                     # Preserves empty dirs in git
```

## Step-by-step

### 1. Choose your taxonomy

What top-level folders will the wiki have? Think of the coherent buckets your content falls into. Keep it to 4–8 top-level entries — more and you get fragmentation; fewer and you collapse everything into one place.

Examples:

- `engineering-ops` uses `entities/` `platform/` `workers/` `workflows/` `agents/`
- `research-wiki` uses `raw/` `wiki/`
- `book-companion` uses `raw/chapters/` `wiki/characters/` `wiki/places/` `wiki/themes/` `wiki/plot-threads/`

### 2. Write `memex.config.json`

Copy `templates/profiles/generic/memex.config.json` as the starting point. Fill in:

- `profile` — your profile name
- `allowedTopLevel` — every top-level folder / file name that should be allowed
- `readmeRequired` — slug patterns where the first write must be README.md (`entities/*`, `wiki/entities/*`, etc.)
- `frontmatter.required` — which frontmatter fields are mandatory
- `frontmatter.enum.type` — the allowed values for the `type:` field on your pages
- `index.sections` — the top-level sections your index will maintain
- `codeToDocMapping` — if this profile is for a codebase, define the rules linking code to docs

### 3. Write `AGENTS.md`

This is the contract your profile makes Claude follow. Include:

- What the three layers are (raw / wiki / schema)
- When Claude should read existing pages before writing new ones
- Profile-specific forbidden actions
- A section 3 table linking triggers to required artifacts

Use `templates/profiles/engineering-ops/.memex/AGENTS.md` and `templates/profiles/research-wiki/.memex/AGENTS.md` as references.

### 4. Write `README.md`

The folder map. Plain list of what goes where. See existing profiles for examples.

### 5. Seed `index.md` and `log.md`

`index.md` has section headings + placeholder `*No X yet.*` text. `log.md` has one seed entry:

```
## [YYYY-MM-DD] init | <profile-name> profile scaffolded
```

### 6. Create empty folders with `.keep`

Every folder Claude might need to write into should exist at scaffold time so `/memex:init` produces a recognisable tree. Drop a `.keep` file inside.

### 7. Write `CLAUDE.md`

Template for the project-level `CLAUDE.md` that points at the scaffolded `.memex/`. Short. Mentions `/memex:init` was run, links to AGENTS and index, project-specific placeholder at the bottom.

### 8. Test

Scaffold a throwaway project:

```bash
cd /tmp/test-project
# Symlink or point the plugin at your local fork
/memex:init your-profile
```

Write a file in each `readmeRequired` folder. Write a file outside `allowedTopLevel`. Write a `README.md` without frontmatter. Make sure each gets blocked with a sensible message.

### 9. Contribute (optional)

Open a PR adding your profile under `templates/profiles/<name>/`. Include:

- The full tree
- A one-line entry for the profile in [`README.md`](../README.md)'s Profiles table
- A one-line entry in [`docs/README.md`](README.md)'s Profiles table
- An entry in `examples/<name>-demo/` showing a worked example

## Common pitfalls

- **`allowedTopLevel` mismatch with your tree.** If you reference `foo/` in readme-required but forget to add it to allowedTopLevel, writes into that folder will fail the path-guard before reaching the readme-required check. Keep both in sync.
- **Frontmatter `type` enum too narrow.** If you restrict `type` to `['entity', 'concept']` and later want to add summaries, every summary page will fail `frontmatter-check`. Enum it broader than you think you need.
- **`.keep` files left in production.** Once a folder has real content, remove its `.keep` in a commit — otherwise the profile template has stale placeholders.
