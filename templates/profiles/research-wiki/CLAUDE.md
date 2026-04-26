# {{ProjectName}} — Claude Instructions

A research wiki managed by [Memex](https://github.com/anthril/claude-memex) (research-wiki profile), inspired by [Andrej Karpathy's `llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Agent contract

See [.memex/AGENTS.md](.memex/AGENTS.md). Core rule: the LLM writes the wiki, the human curates sources and asks questions.

## The three operations

- **Ingest** — `/memex:ingest <path>` on a file under `raw/`
- **Query** — `/memex:query <question>`
- **Lint** — `/memex:lint`

## Key indices

- [.memex/README.md](.memex/README.md) — folder map
- [.memex/index.md](.memex/index.md) — page catalogue
- [.memex/log.md](.memex/log.md) — chronological ledger
- [.memex/.open-questions/](.memex/.open-questions/) — unresolved items

## How the docsite shows this wiki

The optional [memex-docsite](https://github.com/anthril/claude-memex/blob/main/docs/docsite.md) reads `memex.config.json#/index.sections` for the sidebar's "Sections" nav, and `frontmatter.enum.type` for the page-type badges. Rename a section or add a new content type by editing the JSON — the docsite reflects it on next reload. Run `memex-docsite serve` (after `pip install -e ".[docsite]"`) to browse this wiki locally.

## Project-specific additions

<!-- Put project-specific Claude instructions here. -->
