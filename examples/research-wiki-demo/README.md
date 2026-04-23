# research-wiki demo

A **fully-realised** worked example of `/memex:ingest` on a research-wiki profile. See [WALKTHROUGH.md](WALKTHROUGH.md) for the full story — what happened, what was produced, and how each file cross-references the others.

The directory contains both the input source AND the derived wiki, so you can diff the two. This is the concrete answer to "can Memex actually do an end-to-end ingest" — the contract is stored in the repo and verified by `tests/test_demo_ingest.py`.

## Not for use

This folder is illustrative. Don't import it, clone from it, or treat it as a library.
