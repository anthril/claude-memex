---
title: Open questions
slug: open-questions
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Open questions

Unresolved cross-cutting items. One file per question, kebab-case slug.
Resolved questions move to `.resolved/` with a dated `## Resolution`
section.

Use `/memex:open-q <title>` to file a new one.

In ventures, open questions often bubble up from:

- An interview that contradicts a current hypothesis (and you're not sure
  which side to trust yet)
- A test card that's hard to design — the hypothesis isn't yet falsifiable
  in a cost-effective way
- A regulatory or legal unknown that affects scope
- An architectural choice with no clear winner during MVP planning
- A channel that *should* work for the segment but no one in the team has
  worked with it before

## Required: link the related files

Every open question **must** include a `## Related files` section with
markdown links to every page the question touches: the hypothesis /
interview / test card / ADR / VPC entry that prompted it, and any pages
whose claims will need updating once it's resolved. Use `[label](relative/path)`;
bare paths do not count — the link graph and lint skill only pick up real
markdown links.

For a question raised by a contradictory interview, link both the
interview and the hypothesis it contradicts. For an architectural choice,
link the relevant ADR and the MVP spec sections that depend on each
option. For a regulatory unknown, link the BMC's "Key Partners" or "Cost
Structure" cell where the answer would land.

## When to resolve

A question is ready to resolve when:

1. There's a written answer in a wiki page (not just in the question file
   itself)
2. The pages whose claims would have changed have actually changed
3. The hypothesis status has been updated, if applicable

Then move the file to `.resolved/<YYYY-MM-DD>-<slug>.md` with a final
`## Resolution` section pointing to the answer.
