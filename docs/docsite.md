# memex-docsite

A self-hosted browsable HTML view over a memex wiki. Ships in claude-memex
as an **optional dependency group**: hooks remain stdlib-only, the docsite
adds Starlette + Uvicorn + Jinja2 + Mistune + PyYAML.

## Quick start

```bash
# Inside any project that has a memex.config.json:
pip install -e "claude-memex[docsite]"

# Local dev viewer with live writes:
memex-docsite serve

# Static export (read-only, suitable for GitHub Pages / Cloudflare Pages):
memex-docsite build --out ./dist

# Validate configuration and surface broken links:
memex-docsite check
```

The CLI walks up from the current directory looking for `memex.config.json`,
just like the hooks do. Every `.md` file under the wiki root becomes a route.

## Phases

The docsite ships in phases. Phase 1 (this release) is the read-only
viewer. Future phases add search + graph, write features, annotations,
and Docker packaging.

| Phase | Surface                                                  | Status     |
| ----- | -------------------------------------------------------- | ---------- |
| 1     | Markdown renderer, sidebar nav, dark mode, static export | ✅ shipped |
| 2     | `/search`, `/graph`, `/api/graph` (link-graph viz)       | ✅ shipped |
| 3     | `/open-questions` and `/rules` submission forms          | ✅ shipped |
| 4     | First-party inline annotations                           | ✅ shipped |
| 5     | Page-level comment threads                               | ✅ shipped |
| 6     | Docker self-host image                                   | ✅ shipped |
| 7     | Polish: backlinks, TOC, breadcrumbs, mobile              | ✅ shipped |

### Phase 2 surfaces

- **`/search?q=<query>&n=<top_n>`** — server-side retrieval. Uses the
  same grep ranking as the `user-prompt-context` UserPromptSubmit hook,
  so the docsite and the in-session memex agree on what 'relevant' means.
  When `search.engine` in `memex.config.json` is `qmd` and the `qmd`
  binary is on PATH (or pointed at by `MEMEX_QMD_BIN`), the docsite uses
  it for BM25 + vector retrieval and falls back to grep on failure.

- **`/graph`** — interactive link graph rendered as Mermaid in the browser.
  Toggle "hide orphans" and download the Mermaid source with one click.
  Mermaid is **vendored** at `static/vendor/mermaid.min.js` so the graph
  works offline and behind air-gapped reverse proxies. If JS fails for any
  reason, the page falls back to the raw Mermaid source as text.

- **`/api/graph`** — JSON view of the same data:
  ```json
  {
    "nodes": [{"slug": "...", "title": "...", "type": "concept", "is_hidden": false}],
    "edges": [{"source": "...", "target": "..."}],
    "summary": {
      "node_count": 12, "edge_count": 35,
      "orphans": ["..."], "hubs": ["..."], "dead_ends": ["..."]
    }
  }
  ```

### Phase 3 surfaces — submissions

Two writeable surfaces. Both are gated by `docsite.writeFeatures` in
config (default `[]`) and run through the same `frontmatter-check.py`
hook validator a Claude Code write would, so the docsite never produces
a file the hook would have rejected.

- **`/open-questions`** — list active and resolved questions; `+ Submit`
  button when writes are enabled. Each entry has a "Mark resolved"
  inline form that moves the file under `.open-questions/.resolved/`
  with `status: resolved`, `resolved_by`, and `resolved_at` frontmatter.

- **`/rules`** — list and submit rules. Body is markdown.

To enable, add to `memex.config.json`:

```json
{
  "docsite": {
    "writeFeatures": ["open-questions", "rules"]
  }
}
```

Both POST endpoints honour the configured `auth` mode:
| Mode    | What the form needs                                              |
| ------- | ---------------------------------------------------------------- |
| `none`  | Nothing — submitters can optionally type a name; defaults to "anonymous". |
| `token` | A `_memex_token` form field (or `Authorization: Bearer …` header, or `memex_token` cookie) matching `MEMEX_DOCSITE_TOKEN`. |
| `proxy` | An `X-Forwarded-User` header set by the upstream proxy.          |

Files end up at:
- `<root>/.open-questions/<slug>.md` (active)
- `<root>/.open-questions/.resolved/<slug>.md` (resolved)
- `<root>/.rules/<slug>.md`

### Phase 4 surfaces — inline annotations

Highlight any text on any page and attach a note. No third-party SaaS,
no embed scripts. Annotations are markdown files at:

```
<root>/.annotations/<page-slug>/<annotation-id>.md
```

with frontmatter encoding the W3C Web Annotation Data Model:

```yaml
---
title: Annotation on architecture/concept
slug: 7f3e21a4b5c6d7e8
type: annotation
status: active                    # active | deleted
created: 2026-04-26T15:42:00Z
updated: 2026-04-26T15:42:00Z
author: alice
visibility: public                 # public | group | private
page: architecture/concept
selector:
  type: TextQuoteSelector
  exact: "the hippocampus binds episodes"
  prefix: "consolidation. "
  suffix: " for replay"
position:
  type: TextPositionSelector
  start: 1942
  end: 1973
replies_to: null                   # or a sibling annotation id
---

The "rapid binding" framing here conflicts with the schema-lattice
description on `wiki/concepts/memory.md` — flag for review.
```

#### Routes (all under `/api/annotations/<page-slug:path>`)

| Method   | Auth required           | Behaviour                                   |
| -------- | ----------------------- | ------------------------------------------- |
| `GET`    | no (visibility filtered) | List annotations for a page, ordered by `created`. |
| `POST`   | yes                     | Create a new annotation; returns 201 + JSON. |
| `PATCH`  | yes (author-only)        | Update body / visibility on an existing annotation. |
| `DELETE` | yes (author-only)        | Soft-delete (status flips to `deleted`, body cleared). |

Replies are siblings with `replies_to: <parent-id>`. Threading is
client-side — the sidebar groups `replies_to` matches under each parent.

#### Frontend

A vanilla ES module at [`static/annotations.js`](../memex_docsite/static/annotations.js) implements:

- W3C **TextQuoteSelector** + **TextPositionSelector** anchoring
  (~250 lines, no external libs). Position is the fast first-pass match;
  if the page text shifted, prefix/suffix scoring picks the most-likely
  match across multiple occurrences.
- A floating "📝 Annotate" button that appears next to any text
  selection inside the rendered article.
- A right-side sidebar showing the annotation, its replies, and an
  inline reply form when writes are enabled.
- A new-annotation form with a visibility picker (public/group/private).
- Highlights painted as `<mark class="memex-annotation">`. Multi-element
  ranges are wrapped per-text-node so highlights work across HTML
  structure (headings, lists, code, tables).

#### Visibility model

| Setting   | Who sees it                                           |
| --------- | ----------------------------------------------------- |
| `public`  | Everyone — even anonymous readers.                    |
| `group`   | Authenticated users only (auth ≠ none, not anonymous). |
| `private` | The author only (matched on `author` field).          |

#### Per-page opt-out

```yaml
---
title: My private page
annotations: false
---
```

The annotations script is not loaded; the floating button doesn't
appear; the sidebar is omitted.

#### Enabling

```json
{
  "docsite": {
    "writeFeatures": ["annotations"],
    "annotations": {
      "defaultVisibility": "public",
      "allowAnonymous": true
    }
  }
}
```

Default visibility lands on every new annotation that doesn't set its
own. Set `allowAnonymous: false` to require authentication for write
ops (combine with `auth: token` or `auth: proxy`).

### Phase 5 surfaces — page-level comments

A discussion thread at the bottom of every content page, stored as
JSONL — append-mostly, easy to diff, easy to back up.

**Storage:** one file per page at `<root>/.comments/<flat-slug>.jsonl`.
The page slug's `/` separators are replaced with `__` so each page maps
to one file (avoids deeply nested empty folders).

```jsonl
{"id":"f3a1b2c3d4e5f6a7","author":"alice","visibility":"public","created":"2026-04-26T15:42:00Z","updated":null,"body":"Nice page.","replies_to":null,"status":"active"}
{"id":"77b8...","author":"bob","visibility":"public","created":"2026-04-26T15:45:00Z","updated":null,"body":"Agreed.","replies_to":"f3a1b2c3d4e5f6a7","status":"active"}
```

**Routes (under `/api/comments/<page-slug:path>`):**

| Method   | Auth required           | Behaviour                                   |
| -------- | ----------------------- | ------------------------------------------- |
| `GET`    | no (visibility filtered) | List comments for a page, ordered by `created`. |
| `POST`   | yes                     | Append a new comment. `replies_to` links to a parent id. |
| `PATCH`  | yes (author-only)        | Edit body / visibility on an active comment. |
| `DELETE` | yes (author-only)        | Soft-delete: status flips to `deleted`, body cleared. |

**Frontend** ([`static/comments.js`](../memex_docsite/static/comments.js))
renders threaded discussion at the bottom of each rendered page,
including a new-comment form (with visibility picker) and per-thread
reply forms. Loaded only when `comments` is in `writeFeatures`. Per-page
opt-out via `comments: false` frontmatter.

**Enabling:**

```json
{
  "docsite": {
    "writeFeatures": ["annotations", "comments"]
  }
}
```

**When to use comments vs annotations:**

| Use case                                              | Annotation | Comment |
| ----------------------------------------------------- | :--------: | :-----: |
| "This sentence is wrong / unclear / needs a citation" |     ✓      |         |
| "Long discussion on the page as a whole"              |            |    ✓    |
| Anchor a note to a specific selection                  |     ✓      |         |
| Searchable end-of-page thread                          |            |    ✓    |

A site-wide feed of recent comments lives at **`/comments`** and
shows the most-recent visible activity across every page.

### Phase 6 surfaces — Docker self-host

A self-contained image lives in the repo. See
[`docs/docker.md`](docker.md) for the full guide; the short version:

```bash
docker build -t claude-memex-docsite .
docker compose up -d                  # uses ./docker-compose.yml + .env
```

The image runs as non-root `uid=1000`, mounts the host wiki at
`/wiki`, exposes port 8000, and ships a `/api/health` healthcheck.
Three deployment shapes are documented (nginx, Caddy, Traefik) plus
a Tailscale sidecar pattern for tailnet-only access.

**Bug fixed during Phase 6:** the Phase 3 submissions code reached
into `hooks/scripts/_lib/frontmatter.py` for its validator, which
worked in editable installs but broke in any wheel-style install
(including the Docker image). The validator now lives natively in
`memex_docsite/frontmatter.py` with a parity test
([`tests/test_docsite_frontmatter_parity.py`](../tests/test_docsite_frontmatter_parity.py))
that asserts both implementations agree on flat-frontmatter
inputs — so docsite writes still match what the PostToolUse hook
would have accepted.

### Phase 7 surfaces — polish

**Breadcrumbs.** Every nested page renders a `Home › Folder ›
Subfolder` strip above the article. Top-level pages omit it (only
"Home" would be shown — adds noise without value).

**Backlinks panel.** A right-rail "Linked from" list of every page
that points at the current page. Built from the same graph the
`/graph` view consumes — no parallel index. The graph is cached in
memory for 5 seconds per app instance so a single page-load batch
doesn't trigger N graph rebuilds. The static exporter builds the
graph once for the whole export.

**Table of contents.** Right-rail "On this page" anchor list
auto-generated from the page's H2 + H3 headings. Suppressed when a
page has fewer than two such headings (most short notes don't need
one).

**Mobile.** Three breakpoints:

| Width                     | Layout                                                     |
| ------------------------- | ---------------------------------------------------------- |
| ≥ 1024px                  | Sidebar + content + right rail (3 columns).                |
| 720–1023px                | Sidebar + content (right rail hidden).                     |
| < 720px                   | Hamburger reveals an overlay sidebar; content fills viewport. |

**Keyboard.** Press `/` from anywhere on the page (when not already
typing in an input) to focus the search box. Press `Esc` from the
search box to blur it. Familiar from GitHub / Quartz / readthedocs.

**Caching.** The link graph is built lazily on first request and
held for 5 seconds per app instance — long enough that a single page
view (which fetches `/api/graph` indirectly) doesn't rebuild N times,
short enough that wiki edits surface in the next refresh without an
explicit invalidation.

## Config

Add a `docsite` block to `memex.config.json`. All fields are optional;
absent fields fall back to documented defaults.

```json
{
  "docsite": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8000,
    "auth": "none",
    "title": "My Project Wiki",
    "theme": "auto",
    "showHidden": true,
    "writeFeatures": ["open-questions", "rules", "comments", "annotations"],
    "exportPath": "dist/",
    "annotations": {
      "defaultVisibility": "public",
      "allowAnonymous": true,
      "indexable": false
    }
  }
}
```

| Field             | Default       | Notes                                                                               |
| ----------------- | ------------- | ----------------------------------------------------------------------------------- |
| `enabled`         | `true`        | Set false to disable `serve` entirely.                                              |
| `host`            | `127.0.0.1`   | Bind interface for `serve`. Override with `--host`.                                 |
| `port`            | `8000`        | Override with `--port`.                                                             |
| `auth`            | `none`        | One of `none`, `token`, `proxy`. See "Auth" below.                                  |
| `title`           | derived       | Defaults to `"<Profile> — Memex"`.                                                  |
| `theme`           | `auto`        | One of `auto`, `light`, `dark`. Readers can override via the toggle.                |
| `showHidden`      | `true`        | When false, omits dot-folders (`.open-questions/`, `.rules/`, `.annotations/`).     |
| `writeFeatures`   | `[]`          | Phase-3+ gate. List the surfaces that accept POST. Phase 1 ignores this field.      |
| `exportPath`      | `dist/`       | Default output dir for `memex-docsite build`.                                       |
| `annotations.*`   | various       | Phase-4 settings; ignored by Phase 1.                                               |

## Auth modes

| Mode    | Use case                                        | Behaviour                                                                                  |
| ------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `none`  | Local-only `serve`                              | Bind to `127.0.0.1` only. No auth. Submissions tagged `author: anonymous` (Phase 3+).      |
| `token` | Docker self-hosted                              | Single shared `MEMEX_DOCSITE_TOKEN` env var. Bearer header on POST/PATCH/DELETE.           |
| `proxy` | Docker behind Tailscale / Cloudflare Access     | Trust `X-Forwarded-User` from the upstream proxy; that header becomes the submission `author`. |

(Auth is wired in Phase 3; Phase 1 routes are all GET.)

## Static export caveats

- Write features are disabled in `build` output. The page footer carries a
  `static` badge. POST forms are omitted by the templates.
- Folder URLs work because each page is written as `<slug>/index.html`.
  Hosts that serve `index.html` for directory requests (GitHub Pages,
  Cloudflare Pages, S3 static-website hosting) will route correctly.
- The `raw/` directory is copied verbatim so PDFs and images keep their URLs.

## Per-page opt-outs (frontmatter)

| Frontmatter           | Effect                                                                  |
| --------------------- | ----------------------------------------------------------------------- |
| `comments: false`     | Suppresses Phase 5 comment threads on this page.                        |
| `annotations: false`  | Suppresses Phase 4 annotation toolbar on this page.                     |
| `private: true`       | Page is omitted from sidebar nav and search; still reachable by URL.    |

(Frontmatter knobs land alongside the corresponding phase.)

## Relationship to existing slash commands

The docsite reads the same data the slash commands read:

- `/memex:graph` writes JSON the docsite's `/graph` view will render.
- `/memex:open-q` and the docsite's `/open-questions` POST endpoint write
  identical files to `<root>/.open-questions/<slug>.md`.
- `/memex:lint` and `memex-docsite check` agree on broken links because
  they share `_lib/index_parse.py`'s wikilink regex.

The docsite is purely a presentation layer — every write goes through
the same PostToolUse hook chain (e.g., `frontmatter-check.py`) regardless
of whether the file came in via Claude Code or a browser POST.
