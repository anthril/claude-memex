---
title: Open questions
slug: open-questions
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-27
---

# Open questions

Unresolved cross-cutting items. One file per question, kebab-case slug. Resolved questions move to `.resolved/` with a dated `## Resolution` section.

Use `/memex:open-q <title>` to file a new one.

In research-project, open questions often bubble up from:

- An experiment whose result contradicts an established synthesis
- A hypothesis that the team isn't sure how to test yet
- An architectural decision with no clear winning option
- A gap in the literature review — a claim we can't find strong evidence for

## Required: link the related files

Every open question **must** include a `## Related files` section with markdown links to every page the question touches: the experiment / synthesis / ADR / literature-review entry that prompted it, and any pages whose claims will need updating once it's resolved. Use `[label](relative/path)`; bare paths do not count — the docsite link graph and `wiki-lint` skill only pick up real markdown links.

For a question raised by a contradictory experiment result, link both the experiment write-up and the synthesis it contradicts. For an architectural decision, link the relevant ADR(s) and the spec sections that depend on each option. For a literature gap, link the literature-review entry and the wiki page that asserts the claim.
