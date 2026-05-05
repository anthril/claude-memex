---
title: Agent Contract (venture)
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Agent Contract

Binding contract for agents operating on this venture wiki.

The LLM authors and maintains the venture wiki; the human runs interviews,
makes pivot/refine decisions, and approves connector mutations.

## 1. Before starting work

1. Read [README.md](README.md) for the folder map
2. Read [index.md](index.md) — catalogue of current pages
3. Read the tail of [log.md](log.md) — recent chronology
4. Check [`.open-questions/`](.open-questions/) for items relevant to your task
5. Check [`.project-owner-actions/`](.project-owner-actions/) for owner-only blockers
6. Read [`.rules/`](.rules/) — especially the four curriculum guard-rails:
   - [`hypothesis-rules.md`](.rules/hypothesis-rules.md)
   - [`customer-discovery-rules.md`](.rules/customer-discovery-rules.md)
   - [`prototype-vs-mvp-rules.md`](.rules/prototype-vs-mvp-rules.md)
   - [`pivot-refine-rules.md`](.rules/pivot-refine-rules.md)

## 2. The phase tree

| Folder | Phase | What lives here |
|---|---|---|
| `00-vision/` | Pre-discovery | Vision sketch, day-in-the-life |
| `01-hypotheses/` | Pre-discovery | Hypothesis register (canonical), BMC v1 |
| `02-customer-discovery/` | Discovery (Ch. 3) | Segments, profiles, interview guides, interview logs, test cards, learning cards |
| `03-value-proposition/` | VPC (Ch. 4) | Value Proposition Canvases, versioned |
| `04-competitors/` | Competitor analysis (Ch. 4) | UVP, competitor table, SWOTs, shadow BMCs, insights |
| `05-business-model/` | BMC (Ch. 2) | BMC v2, v3 ... |
| `06-relationships-channels/` | Channels (Ch. 8) | Get/keep/grow, channel strategy, funnel, churn |
| `07-validation/` | Verify/pivot/refine (Ch. 1) | Pivot-refine log |
| `08-prototype/` | Week 7 studio | Paper, digital (Figma), feedback |
| `09-mvp/` | MVP (Ch. 6 + engineering bridge) | Spec, metrics, tech stack, architecture, schema, deploy, analytics, feasibility |

The numeric prefix is load-bearing — `phase-router` uses it to decide what to
do next. Don't add new top-level folders without updating
`memex.config.json#/allowedTopLevel`.

## 3. Required artifacts

| Trigger | Required doc |
|---|---|
| Venture started | `00-vision/vision-sketch.md` + `00-vision/day-in-life.md` |
| New hypothesis stated | Append to `01-hypotheses/hypothesis-register.md` |
| New segment defined | `02-customer-discovery/segments/<slug>/README.md` (+ `profile.md`, `interview-guide.md`, `early-adopters.md`) |
| Interview run | `02-customer-discovery/segments/<slug>/interviews/interview-NNN.md` (append-only) |
| Test designed | `02-customer-discovery/test-cards/TC-NNN.md` |
| Test concluded | `02-customer-discovery/learning-cards/LC-NNN.md` linking back to TC-NNN |
| VPC built or refined | `03-value-proposition/vpc-<segment>-vN.md` |
| Competitor added | `04-competitors/competitor-table.md` row + `04-competitors/swot/<competitor>/README.md` |
| BMC version bumped | `05-business-model/bmc-vN.md` |
| Pivot or refine decision | Append to `07-validation/pivot-refine-log.md` |
| Prototype made | `08-prototype/paper/<slug>.md` or `08-prototype/digital/<slug>/README.md` |
| MVP scoped | `09-mvp/mvp-spec.md` + `09-mvp/mvp-metrics.md` |
| Architecture decision | `09-mvp/architecture/ADR-NNN-<slug>.md` |
| Open question | `.open-questions/<slug>.md` |

All pages require full frontmatter (`title`, `slug`, `type`, `status`,
`owner`, `created`, `updated`). The `path-guard` and `frontmatter-check`
hooks enforce this at write-time.

## 4. Hypothesis discipline

- Every hypothesis must be **falsifiable** — see
  [`.rules/hypothesis-rules.md`](.rules/hypothesis-rules.md)
- Every hypothesis carries an explicit `status:` (`draft` / `active` /
  `deprecated` / `superseded`)
- When a learning card flips a hypothesis, **never delete** the old version —
  set its status and append a new entry that links back to the test/learning
  card pair

## 5. Interview discipline

- Interview logs are **append-only**. Never edit a logged interview after
  the fact. If the notes are wrong, file a follow-up note in the same
  segment's `interviews/` folder.
- Interview guides ≤ 30 minutes, open questions, ask "why / why not / who
  else / can we follow up."
- After every batch of interviews, run `interview-analyse` to update the
  hypothesis register.

## 6. Cross-references

Every page links to:

- The pages it depends on (segment a profile is for, hypothesis a test
  references, BMC version a hypothesis flip caused, etc.)
- From its parent index section

The `index-update.py` and `stop-stale-check.py` hooks catch missing or
stale cross-references at session stop.

## 7. Forbidden actions

- Editing a logged interview (immutable once filed)
- Leaving inline `TODO` / `TBD` markers — file under `.open-questions/`
- Deleting hypothesis-register entries — set status to `deprecated` /
  `superseded` and link to the evidence
- Editing `memex.config.json` without filing an open question explaining why
- Bumping a BMC version without recording which hypothesis flips drove the
  change in the new version's frontmatter `notes:` field
- Mislabeling a prototype as an MVP — the
  [`prototype-vs-mvp-rules.md`](.rules/prototype-vs-mvp-rules.md) gate
  refuses

## 8. Compounding, not rediscovery

- When a learning card flips a hypothesis, **update every page that cites
  it** — VPC entries, BMC cells, channel choices. The point of the wiki is
  that you don't repeat the discovery.
- When a new segment is defined, the existing VPCs, BMCs, and channel
  strategies need a "does this still hold?" pass. The
  `customer-discovery-orchestrator` agent runs this pass automatically when
  a segment is added.

## 9. Connector mutations

Any skill that calls Supabase / Cloudflare / Figma / Vercel must follow the
[connector-confirmation idiom](https://github.com/anthril/startup-factory/blob/main/shared/reference/connector-confirmation.md):
read-only by default, mutations gated behind `AskUserQuestion` with a
preview block. There is no auto-yes mode.

---

*This contract derives from the COMP1100/COMP7110 curriculum; see
`shared/reference/curriculum-citations.md` in the
[`@anthril/startup-factory`](https://github.com/anthril/startup-factory)
marketplace for the full source mapping.*
