# Tests

End-to-end test harness for the Memex plugin. Uses `pytest` with temporary scaffolded projects.

## Layout

```
tests/
├── README.md                    # this file
├── conftest.py                  # shared fixtures (scaffold every profile into a tmp dir)
├── test_lib.py                  # unit tests on hooks/scripts/_lib/* (pure functions)
├── test_hooks_pretooluse.py     # path-guard, readme-required, doc-required, ingest-doc-link, frontmatter-precheck
├── test_hooks_posttooluse.py    # frontmatter-check, index-update
├── test_hooks_session.py        # session-start-context, user-prompt-context, stop-*, precompact, session-end
├── test_unicode_paths.py        # kebab-case across Japanese, Greek, Cyrillic, Arabic, Hebrew, Thai, CJK, etc.
├── test_update_check.py         # update-check hook + _lib/version SemVer compare
├── test_migration.py            # scripts/migrate_from_operations.py against a synthetic .operations/ tree
├── test_demo_ingest.py          # contract verification for examples/research-wiki-demo/
├── test_profiles.py             # every shipped profile scaffolds cleanly and its canonical path is accepted
├── test_attribution.py          # Karpathy attribution present where it must be
└── fixtures/
    └── mock_qmd/qmd             # mock qmd binary for qmd-engine tests (generated on-demand by the test)
```

Current count: **227 tests**, ~5 seconds on a modern laptop.

## Running

Python 3.10+. Install dev deps:

```bash
pip install -e ".[dev]"
# or just pytest if you don't want ruff + mypy
pip install pytest
```

Then:

```bash
pytest                                # all tests
pytest -v                             # verbose
pytest tests/test_unicode_paths.py    # one file
pytest -k migration                   # by keyword
```

All tests are hermetic — each uses a temporary directory that's cleaned up after the test. No network calls (the update-check test uses a fixture file via `MEMEX_UPDATE_CHECK_JSON`). No state is shared between tests.

## Coverage

The harness covers:

- Every hook script's happy path + at least one failure path
- Every shipped profile (5 of them) — parametrised across 6 check types
- The config merging logic (defaults, overrides)
- Frontmatter parsing / validation (including enum constraints)
- Path utilities — ASCII and Unicode kebab, dated folders
- Index parsing — section detection, markdown link extraction, wikilink extraction, reference lookup
- Glob-to-regex + substitute helpers in `_lib/patterns.py`
- qmd integration via a mock binary (`MEMEX_QMD_BIN` env override)
- Update-check hook — opt-in gating, 24h cache TTL, cache-expiry refetch, graceful failure modes
- Migration script — dry-run vs execute, config inference from target project shape, refusal conditions
- Worked ingest demo — every cross-reference resolves, every page is indexed, log has parseable entries
- SemVer compare edge cases — release beats prerelease, lexicographic prerelease compare

What the harness does NOT cover:

- Claude Code's own hook invocation plumbing (that's Anthropic's test responsibility)
- Real qmd binary behaviour (mock-only — real integration requires a working `qmd` install)
- `/memex:*` slash command execution (they're prompt templates; testing them is effectively testing Claude)
- GitHub API itself (we exercise the parse/cache/compare logic via fixture, not real network traffic)
