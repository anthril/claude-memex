# {{ProjectName}} — Reading companion

A book-companion wiki managed by [Memex](https://github.com/anthril/claude-memex).

## Contract

See [.memex/AGENTS.md](.memex/AGENTS.md). The LLM builds the character/place/theme/plot-thread wiki as you read, chapter by chapter. Strict rule: no spoilers beyond the current reading horizon (tracked in `log.md`).

## Reading loop

1. Read a chapter
2. `/memex:ingest .memex/raw/chapters/<NN>-<slug>.md`
3. Review the updates; ask questions via `/memex:query`
4. Continue

## Indices

- [.memex/README.md](.memex/README.md)
- [.memex/index.md](.memex/index.md)
- [.memex/timeline.md](.memex/timeline.md)
