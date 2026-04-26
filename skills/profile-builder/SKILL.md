---
name: profile-builder
description: Interactively build a custom Memex profile tailored to a project's actual folder shape. Surveys the project with Glob/Grep, classifies the project type, asks the user targeted questions about taxonomy and gating, and writes a complete memex.config.json + .memex/ tree + CLAUDE.md + AGENTS.md. Invoked by /memex:init-profile, or when the user says "help me build a profile", "make a memex profile for this project", or "none of the profiles fit".
triggers:
  - "/memex:init-profile"
  - "help me build a memex profile"
  - "make a profile for this project"
  - "none of the memex profiles fit"
  - "customise a profile"
allowed-tools: Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# Build a custom Memex profile

Interactive. The goal is to produce a complete, hook-valid scaffold in one session — not a patch-kit the user has to finish by hand. Work the steps in order.

## 1. Safety check — abort if already scaffolded

Refuse to run if the current project already has a Memex wiki:

```bash
[ -d ".memex" ] && echo "has .memex/"
[ -f "memex.config.json" ] && echo "has memex.config.json"
```

If either exists, list what's there and stop. Suggest `/memex:lint` to audit the existing wiki, or hand-editing per `docs/profile-authoring.md`. Do not overwrite.

## 2. Survey the project

Use Glob + Read to build a mental model of what this project is. Collect:

**Top-level folders (depth 1):**

```bash
# via Glob with pattern "*" in project root
```

**Type markers — language / framework:**

| Marker | Signal |
|---|---|
| `package.json` | Node / TypeScript / JS project |
| `pyproject.toml`, `requirements.txt`, `setup.py` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `Gemfile`, `*.gemspec` | Ruby |
| `pom.xml`, `build.gradle` | JVM |
| `composer.json` | PHP |

**Type markers — project shape:**

| Marker | Signal |
|---|---|
| `src/`, `app/`, `pages/`, `components/` | Codebase |
| `supabase/`, `prisma/`, `migrations/`, `sql/` | SaaS with database |
| `functions/`, `workers/`, `edge/` | Serverless / edge |
| `terraform/`, `infra/`, `.github/workflows/` | Infra / ops surface |
| `research/`, `papers/`, `notes/`, `.obsidian/` | Research |
| `hypotheses*`, `roadmap*`, `architecture/`, `evaluation/` | Planning-phase research |
| `chapters/`, `draft/`, `manuscript/` | Writing / book |
| `journal/`, `entries/`, `reflections/` | Personal / journaling |
| `docs/`, `mkdocs.yml`, `docusaurus.config.js` | Documentation site |

**Existing files at root (depth 1):** note any top-level markdown files that hint at existing docs conventions (`ARCHITECTURE.md`, `ROADMAP.md`, `METHODOLOGY.md`, `CONTRIBUTING.md` …).

Print a terse summary to the user: "This looks like a `<classification>` project. Top-level folders: `<a, b, c>`. Marker files: `<x, y>`."

## 3. Pick the starting point

Based on the survey (or the `[base-profile]` argument if the user supplied one), pick the closest built-in profile as a base:

- **SaaS codebase** → `engineering-ops`
- **Research project still in planning** → `research-project`
- **Pure reading / ingest wiki** → `research-wiki`
- **Book reading companion** → `book-companion`
- **Personal journal** → `personal-journal`
- **Anything else** → `generic`

Read the chosen profile's `memex.config.json` and `.memex/` tree from `${CLAUDE_PLUGIN_ROOT}/templates/profiles/<base>/`. These give you the shape you'll customise.

Announce the pick and rationale. Offer the user the choice to switch to a different base before continuing.

## 4. Interview — 4 to 6 targeted questions

Use `AskUserQuestion` when available. Ask in this order, one question per turn unless grouping saves time:

### Q1 — Primary purpose
One sentence: what is this project for? (Offer 3–4 options derived from the survey, plus free-text.)

### Q2 — Current phase
One of: planning, research, active development, maintenance, multiple. This affects which surfaces should be required vs optional. A planning-phase project needs `research/`, `architecture/`, `experiments/`; a maintenance-phase project needs `runbooks/`, `processes/`, `.incidents/`.

### Q3 — Adopt existing folders
Present the surveyed top-level folders as a multi-select. For each one: should this become a top-level wiki surface (with its own `<slug>/README.md` pattern)? Some folders (e.g. `node_modules/`, `.git/`, `dist/`) are obviously not wiki surfaces; filter those out before asking.

For each chosen folder, ask what `type:` values belong there (open-ended — default to the folder name singular-ised).

### Q4 — New surfaces not in the base profile
Free-text. Are there content types this project needs that the base profile doesn't have? Common ones:

- `runbooks/`, `processes/`, `environments/` (ops)
- `planning/prds/`, `planning/rfcs/`, `planning/decisions/` (product / design)
- `research/hypotheses/`, `research/experiments/`, `research/methodology/` (research)
- `benchmarks/`, `evaluation/` (research / ML)
- `contracts/`, `policies/` (legal / compliance)

### Q5 — README gating
Default: every top-level slug folder with a 1:many shape (`entities/*`, `platform/features/*` …) gets README-gated. Confirm or override.

### Q6 — Code-to-doc mappings
Optional. Ask: "Are there code paths that should require a linked wiki page? For example, every edge function under `supabase/functions/<name>/` requires `platform/systems/<name>/README.md`." If yes, collect one or more `(codePattern, requiresDoc, severity)` triples. If unsure, leave `codeToDocMapping: []` — it can be added later via `docs/cookbook.md`.

## 5. Draft the taxonomy — show before writing

Assemble from the interview answers:

- `allowedTopLevel` — always includes `README.md AGENTS.md index.md log.md .open-questions .rules .state` plus every custom top-level from the interview
- `readmeRequired` — the slug patterns from Q5
- `frontmatter.enum.type` — derived from Q3 and Q4; always include `open-question` and `rule`
- `index.sections` — one per content type, always trailing with `Open Questions` and `Recent Activity`
- `datedFolders.paths` — any surface like `.audits`, `.research`, `.incidents` the user selected
- `codeToDocMapping` — from Q6 (or empty)

**Cross-check before printing:** every pattern in `readmeRequired` must have its top-level slot in `allowedTopLevel`. This is the pitfall flagged in [docs/profile-authoring.md](../../docs/profile-authoring.md) — catch it here, not at hook time.

Print the full proposed config + the folder tree to the user. Ask for confirmation or edits. Loop until confirmed.

## 6. Generate — write every file

Once confirmed, write in this order:

1. `memex.config.json` — from the draft
2. `.memex/README.md` — folder map table, one row per top-level slot
3. `.memex/AGENTS.md` — binding contract; fill in the "Required artifacts" table from the interview; use [`templates/shared/agents.md.tmpl`](../../templates/shared/agents.md.tmpl) as the skeleton
4. `.memex/index.md` — one section per `index.sections` entry with the standard `*No X yet. Create <path> to add one.*` placeholder
5. `.memex/log.md` — seed with `## [YYYY-MM-DD] init | <profile-slug> profile scaffolded via /memex:init-profile`
6. `.memex/.open-questions/README.md` — copy from the base profile
7. `.memex/.rules/README.md` — index of rule docs; carry forward any rules from the base profile that still apply
8. `.memex/.state/` — create empty (hook-managed)
9. `.keep` files for every empty folder in the taxonomy
10. `CLAUDE.md` — use [`templates/shared/claude.md.tmpl`](../../templates/shared/claude.md.tmpl) with `{{ProjectName}}` = the current folder name and `{{Profile}}` = the custom slug. If `./CLAUDE.md` already exists, print the template and ask the user to splice it manually rather than overwriting.

Substitute dates: `created:` / `updated:` use today's ISO date. `owner:` defaults to `unassigned` — the user will edit it.

## 7. Offer to contribute the profile upstream

Optional — skip if the user is not inside the plugin repo. Ask: "Save this profile as a reusable template in the Memex plugin so `/memex:init <slug>` works from other projects?" If yes, print the full path where it should live (`templates/profiles/<slug>/`) and the one-line PR entries needed in `README.md`, `docs/README.md`, `commands/memex-init.md`. Do NOT write into the plugin repo automatically — the user should submit the PR themselves.

## 8. Post-scaffold summary

Print a compact summary:

```
Created:
  memex.config.json
  .memex/README.md  .memex/AGENTS.md  .memex/index.md  .memex/log.md
  .memex/<custom-folders>/.keep
  CLAUDE.md

Next 3 actions:
  1. Review .memex/AGENTS.md and set owner: fields
  2. Review memex.config.json#/codeToDocMapping — empty by default; add project-specific mappings
  3. Run /memex:log to verify hooks are active

Optional: pip install -e ".[docsite]" && memex-docsite serve to browse the new wiki

Docs: docs/concepts.md, docs/cookbook.md, docs/docsite.md
```

## 9. Log the decision

Write one line to `.memex/log.md` documenting the taxonomy choices, so the rationale survives into the project's history. Format:

```
## [YYYY-MM-DD] init | custom profile scaffolded — top-levels: <a, b, c>; based on <base-profile>
```

---

## Common pitfalls

- **`allowedTopLevel` / `readmeRequired` mismatch.** Every pattern in `readmeRequired` must have its top-level slot in `allowedTopLevel`. Cross-check before writing.
- **`frontmatter.enum.type` too narrow.** If the user later adds a content type, every page of that type will fail `frontmatter-check`. Enum it broader than the interview strictly required — when in doubt, add it.
- **Overfitting to today's folders.** Projects grow. If the user is sure a surface belongs but has no content yet, add it to the taxonomy now with a `.keep` — cheaper than retrofitting.
- **Assuming `/memex:init-profile` is idempotent.** It is not. The safety check at step 1 is load-bearing.
