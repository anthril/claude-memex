# {{ProjectName}} — Claude Instructions

This project uses the [Memex](https://github.com/anthril/claude-memex) plugin (generic profile).

## Agent contract

See [.memex/AGENTS.md](.memex/AGENTS.md). Hooks enforce the contract at tool-call time; read stderr if a write is blocked.

## Key indices

- [.memex/README.md](.memex/README.md)
- [.memex/AGENTS.md](.memex/AGENTS.md)
- [.memex/index.md](.memex/index.md)
- [.memex/log.md](.memex/log.md)

## How the docsite shows this wiki

The optional [memex-docsite](https://github.com/anthril/claude-memex/blob/main/docs/docsite.md) reads `memex.config.json#/index.sections` for the sidebar's "Sections" nav, and `frontmatter.enum.type` for the page-type badges. Edit the JSON to rename a section or add a content type. Run `memex-docsite serve` (after `pip install -e ".[docsite]"`) to browse this wiki locally.

## Project-specific additions

<!-- Put project-specific instructions here. -->
