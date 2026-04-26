# Journal — Claude Instructions

A private personal-journal wiki managed by [Memex](https://github.com/anthril/claude-memex). Do NOT push to a public remote.

## Contract

See [.memex/AGENTS.md](.memex/AGENTS.md). Key rule: summarise, cross-reference, ask questions — do not therapise.

## Indices

- [.memex/README.md](.memex/README.md)
- [.memex/index.md](.memex/index.md)

## How the docsite shows this wiki

The optional [memex-docsite](https://github.com/anthril/claude-memex/blob/main/docs/docsite.md) reads `memex.config.json#/index.sections` for the sidebar's "Sections" nav, and `frontmatter.enum.type` for the page-type badges. Edit the JSON to rename a section. Keep the docsite local-only (do not expose) — this profile is private. Run `memex-docsite serve --host 127.0.0.1` (after `pip install -e ".[docsite]"`).
