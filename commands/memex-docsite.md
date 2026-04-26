---
description: Start, build, or check the self-hosted docsite for this project's wiki
argument-hint: "[--cwd PATH] (serve [--port N] [--auth MODE] | build [--out DIR] | check)"
allowed-tools: Bash
---

# /memex:docsite

Thin wrapper over the `memex-docsite` CLI. The docsite is an optional
dependency group — if missing, this command prints the install hint
instead of failing silently.

## Usage

```
/memex:docsite serve              # http://127.0.0.1:8000 with live writes
/memex:docsite serve --port 9000
/memex:docsite build              # static export to dist/
/memex:docsite build --out site/
/memex:docsite check              # validate config + surface broken links

# `--cwd` is a top-level flag — pass it BEFORE the subcommand:
/memex:docsite --cwd examples/research-wiki-demo check
```

## Behaviour

1. Verify the docsite extras are installed:
   ```
   python -c "import memex_docsite" 2>/dev/null
   ```
   If that fails, print:
   > The docsite is an optional install. Run:
   > ```
   > pip install -e ".[docsite]"
   > ```
   > then retry `/memex:docsite`.

2. For `serve`:
   - Start `memex-docsite serve` (in the background where the harness allows)
   - Print the bound URL the user should open
   - Remind them that writes (annotations / comments / open-questions / rules)
     append to `log.md` so the next session sees the activity

3. For `build`:
   - Run `memex-docsite build` with the supplied `--out` (default `dist/`)
   - Print the export summary (pages, folder indexes, list pages, assets)

4. For `check`:
   - Run `memex-docsite check`
   - Surface any broken-link / render-error output verbatim
   - Exit non-zero if `check` did

## Notes

- The docsite reads the same `memex.config.json` the hooks do — there is
  no parallel index. Sections nav is driven by `index.sections` +
  `frontmatter.enum.type`.
- The Phase 7 docsite ships in the repo under `memex_docsite/`. See
  [`docs/docsite.md`](../docs/docsite.md) for the full configuration
  guide and [`docs/docker.md`](../docs/docker.md) for self-host.
