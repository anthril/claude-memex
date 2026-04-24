# Cookbook

Practical recipes for customising Memex in a project that already has it installed.

---

## Add a new top-level folder to an existing wiki

Edit `memex.config.json`:

```json
"allowedTopLevel": [
  "README.md", "AGENTS.md", "index.md", "log.md",
  "... existing ...",
  "playbooks"
]
```

Create `playbooks/README.md` with full frontmatter on the next edit. Update `.memex/README.md`'s folder map.

Ideally also file `.open-questions/<slug>.md` explaining *why* the folder is being added so the decision is forensically recoverable.

---

## Add a code-to-doc mapping

You want every new edge function under `supabase/functions/<name>/` to require a corresponding `platform/systems/<name>/README.md`.

```json
"codeToDocMapping": [
  {
    "codePattern": "supabase/functions/*/",
    "requiresDoc": "platform/systems/{1}/README.md",
    "severity": "warn-then-block",
    "stateKey": "edge-fn"
  }
]
```

First write that violates the rule → warning. Second write for the same `<name>` slug → block.

For migrations (files, not folders), use the stricter `severity: block`:

```json
{
  "codePattern": "supabase/migrations/*.sql",
  "requiresDoc": "ANY .md containing the slug OR header `-- Doc: .memex/<path>.md`",
  "severity": "block"
}
```

The `ANY / referencing` phrasing triggers the `ingest-doc-link.py` fallback.

---

## Disable one specific hook for this project

Memex plugin hooks are defined in `hooks/hooks.json` (plugin-owned). You can't easily disable an individual hook on the plugin side. Instead:

- Edit `memex.config.json` to make the hook's matcher effectively no-op. For example, empty `readmeRequired` disables `readme-required.py` without touching the plugin.
- For `doc-required` / `ingest-doc-link`: leave `codeToDocMapping` empty to disable them.
- For `path-guard`: there's no way to disable without editing the plugin. Consider whether you really want to — path-guard is the most protective hook.

If you genuinely need to disable a whole hook, fork the plugin and remove the wiring from `hooks/hooks.json`. Submit a PR with the use case — there may be a config option worth adding.

---

## Enable `qmd` for wiki retrieval

Install `qmd` (`cargo install qmd` or grab a binary from its repo). Then:

```json
"search": {
  "engine": "qmd",
  "maxContextPages": 5
}
```

The `user-prompt-context.py` hook will shell out to `qmd search` and fall back to grep if `qmd` is not on PATH.

---

## Change the log entry prefix format

`log.entryPrefix` is a template with `{date}`, `{event}`, `{subject}` placeholders. If you want ISO timestamps:

```json
"log": {
  "path": "log.md",
  "entryPrefix": "## [{date}] [{event}] {subject}"
}
```

The `grep "^## \[" log.md | tail -N` trick still works.

---

## Silence the index-update nudges for specific folders

If you don't want nudges for a specific folder (e.g. you intentionally keep `.audits/` out of the index):

Edit `index-update.py` to add the folder to its skip list — or, better, open an issue suggesting a config field like `index.ignoreFolders: [".audits"]` that the hook reads.

---

## Increase how much of the log gets injected at session start

Default is the last 5 entries. To change:

```json
"hookEvents": {
  "sessionStart": {
    "injectIndex": true,
    "injectRecentLog": 20
  }
}
```

Consider that `SessionStart` runs before any user message — injected context uses your initial budget. 5–10 entries is usually plenty.

---

## Enable update notifications

Off by default. To opt in:

```json
"hookEvents": {
  "sessionStart": {
    "updateCheck": true
  }
}
```

The check runs at most once every 24h (cached under `.memex/.state/update-check.json`). If GitHub is unreachable or the request times out (3-second cap), the hook exits silently. Corporate / offline environments can point at a mirror:

```json
"updateCheckUrl": "https://my-mirror.example.com/api/memex/releases/latest"
```

---

## Restrict slugs to ASCII-only

The default accepts lowercase / caseless Unicode letters (Japanese, Chinese, Arabic, Greek, Cyrillic, Thai …). If you want to enforce ASCII `[a-z0-9]` for maximum portability:

```json
"naming": {
  "asciiOnly": true
}
```

Extensions (`.md`, `.json`, …) are always ASCII regardless of this setting — keeps the wiki portable across case-insensitive and normalising filesystems.

---

## Opt out of PreCompact snapshots

```json
"hookEvents": {
  "preCompact": { "snapshot": false }
}
```

Useful if you commit `.memex/` to a public repo and don't want per-session artefacts accumulating. You'll lose the synthesis-survives-compaction benefit.

---

## Build a custom profile interactively

If none of the built-in profiles fits your project's shape, run `/memex:init-profile` inside the project. It surveys the existing folders, asks targeted questions, and generates a custom `memex.config.json` + `.memex/` tree tailored to the project. See [`../skills/profile-builder/SKILL.md`](../skills/profile-builder/SKILL.md) for the workflow and [`../examples/custom-profile-demo/WALKTHROUGH.md`](../examples/custom-profile-demo/WALKTHROUGH.md) for a worked example.

---

## Commit policy for `.memex/.state/`

Default: the `.gitignore` shipped by `/memex:init` excludes `.memex/.state/` — per-session state shouldn't be in git history. If you want the `precompact-snapshot` files to be committed (useful for the research angle), remove that line.
