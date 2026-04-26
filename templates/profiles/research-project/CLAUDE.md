# {{ProjectName}} — Claude Instructions

A research + planning project managed by [Memex](https://github.com/anthril/claude-memex) (research-project profile). This profile is a superset of `research-wiki`: it adds first-class research artefacts (hypotheses, methodology, literature review, experiments, prompts, roadmap) and planning surfaces (architecture, systems, evaluation) for projects that will eventually migrate into development.

## Agent contract

See [.memex/AGENTS.md](.memex/AGENTS.md). Core rule: the LLM writes and maintains the wiki; the human curates sources, asks questions, proposes hypotheses, and reviews.

## The three operations

- **Ingest** — `/memex:ingest <path>` on a file under `raw/`
- **Query** — `/memex:query <question>`
- **Lint** — `/memex:lint`

## Key indices

- [.memex/README.md](.memex/README.md) — folder map
- [.memex/index.md](.memex/index.md) — page catalogue
- [.memex/log.md](.memex/log.md) — chronological ledger
- [.memex/research/roadmap.md](.memex/research/roadmap.md) — rolling research roadmap
- [.memex/.open-questions/](.memex/.open-questions/) — unresolved items
- [.memex/.rules/research-to-development.md](.memex/.rules/research-to-development.md) — how surfaces graduate when the project enters dev

## How the docsite shows this wiki

The optional [memex-docsite](https://github.com/anthril/claude-memex/blob/main/docs/docsite.md) reads `memex.config.json#/index.sections` for the sidebar's "Sections" nav, and `frontmatter.enum.type` for the page-type badges. This profile has more enum types than sections (e.g. `methodology`, `literature-review`, `prompt`); those land in synthetic catch-all sections so nothing is hidden. Run `memex-docsite serve` (after `pip install -e ".[docsite]"`) to browse this wiki locally.

## Profile

This project was scaffolded with the `research-project` profile. See `.memex/AGENTS.md` \u00a73 for the trigger-to-artefact table. When the project transitions from planning into active development, consider running `/memex:init-profile engineering-ops` to overlay engineering-ops surfaces alongside the research tree — see [`research-to-development.md`](.memex/.rules/research-to-development.md) for the full graduation path.

## Project-specific additions

<!-- Put project-specific Claude instructions here. -->
