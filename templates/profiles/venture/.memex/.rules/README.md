---
title: Rules (venture)
slug: rules-index
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Rules

Curriculum guard-rails and venture conventions. Three of these are
**blocking** — skills refuse to proceed unless they pass, with a `--force`
override that is logged automatically.

## Files

| File | Purpose | Blocking? |
|---|---|---|
| [hypothesis-rules.md](hypothesis-rules.md) | Falsifiability requirements (Ch. 5) | Yes |
| [customer-discovery-rules.md](customer-discovery-rules.md) | Four-question gate before MVP work (Ch. 3) | Yes |
| [prototype-vs-mvp-rules.md](prototype-vs-mvp-rules.md) | Five-dimension distinction (Ch. 6) | Yes |
| [pivot-refine-rules.md](pivot-refine-rules.md) | Logging requirements for pivots and refines (Ch. 1) | No (logging required, decisions free) |

## Frontmatter requirements

All pages under `00-vision/` through `09-mvp/`, plus all `README.md` /
`AGENTS.md` files, require:

```yaml
title: Human-readable title
slug: kebab-case-slug
type: vision|segment|profile|interview|hypothesis|test-card|learning-card|vpc|competitor|swot|bmc|channel|funnel|prototype|feedback|mvp-spec|adr|schema|deploy-plan|analytics-plan|open-question|rule
status: draft|active|deprecated|superseded
owner: <handle or unassigned>
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

The `frontmatter-check.py` hook validates these on every write.

## Naming

- Folders under `02-customer-discovery/segments/`, `04-competitors/swot/`,
  `08-prototype/digital/`, `09-mvp/architecture/` use kebab-case
- Numbered artifacts (interviews, test cards, learning cards, ADRs) use
  zero-padded three-digit numbering: `interview-001.md`, `TC-001.md`,
  `LC-001.md`, `ADR-001-<slug>.md`
- BMC versions and VPC versions use `bmc-vN.md` and `vpc-<segment>-vN.md`
  with `N >= 1`

## Cross-linking

- Every test card links to the hypothesis it tests
- Every learning card links to the test card it resolves AND the hypothesis
  whose status it changes
- Every VPC links to its segment
- Every SWOT links to the row in `competitor-table.md`
- Every ADR links to the BMC and MVP-spec versions current when it was
  written

## Append-only files

- `02-customer-discovery/segments/*/interviews/interview-NNN.md` — once
  filed, never edited
- `07-validation/pivot-refine-log.md` — append-only chronology
