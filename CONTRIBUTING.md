# Contributing to claude-memex

Thank you for considering a contribution. This is an early-alpha open-source Claude Code plugin — the surface is small, so most contributions either extend a profile, add a hook, or refine an existing skill.

## Before you start

- **Read [`docs/concepts.md`](docs/concepts.md)** — the three-layer model and the reasoning behind hook-enforced doc discipline. Most PRs benefit from aligning with this.
- **Read [`docs/hook-catalog.md`](docs/hook-catalog.md)** if you're touching hooks.
- **Read [`docs/profile-authoring.md`](docs/profile-authoring.md)** if you're adding a profile.
- **Check [`.docs/REPO-PLAN.md`](.docs/REPO-PLAN.md)** (private design doc — ask if you need access) or the [CHANGELOG](CHANGELOG.md) to see what's in flight.

## Kinds of contributions that land easily

| Kind | What we like to see |
|---|---|
| **Bug fix** | Reproducer in `tests/`, minimal diff, clear commit message |
| **New profile** | Full profile tree under `templates/profiles/<name>/`, parametrised tests in `tests/test_profiles.py`, an entry in the README profiles table |
| **New hook** | Follows the style in `hooks/scripts/path-guard.py`: stdin JSON payload, `sys.exit(0)` / `sys.exit(2)`, UTF-8 stderr, config-driven behaviour, tests |
| **Documentation** | Factual corrections, clearer examples, profile authoring tips |
| **Profile-specific rule** | Additions to `.rules/` within an existing profile |

## Kinds of contributions that need discussion first

Open an issue before writing code for:

- Breaking changes to `memex.config.json` schema
- New top-level plugin directories
- Anything that changes hook event wiring in `hooks/hooks.json`
- Adding runtime dependencies (we're stdlib-only by design)

## Dev setup

Python 3.10+. No runtime dependencies beyond the standard library; `pytest`, `ruff`, `mypy` for development.

```bash
git clone https://github.com/anthril/claude-memex.git
cd claude-memex
python -m pip install -e ".[dev]"
```

### Running the docsite locally

If you're touching anything under `memex_docsite/` (or its tests):

```bash
python -m pip install -e ".[docsite,dev]"   # add docsite + dev extras
memex-docsite --cwd examples/research-wiki-demo serve
```

The docsite walks up from `--cwd` looking for `memex.config.json`. The `examples/` projects all have one, so any of them is a quick smoke-test target. See [`docs/docsite.md`](docs/docsite.md) for the full developer guide and [`docs/docker.md`](docs/docker.md) for the Docker workflow.

### Running tests

```bash
pytest                            # full suite (~220 tests, < 10 seconds)
pytest tests/test_hooks_pretooluse.py -v  # one file
pytest -k unicode                 # by keyword
```

### Lint + type check

```bash
ruff check hooks/ tests/ scripts/ memex_docsite/
mypy hooks/ memex_docsite/
```

CI runs both on every PR. Please make sure they pass locally first.

## Coding conventions

- **Hooks follow the reference layout in `path-guard.py`.** Stdin JSON → sanity-check → load config → decide → exit with a clear stderr message.
- **Shared helpers go in `_lib/`.** Don't copy-paste logic across hooks; extract it and add a test.
- **Config-driven, not hard-coded.** If a hook needs a pattern, it reads from `memex.config.json` (+ a sensible default in `_lib/config.py::DEFAULT_CONFIG`).
- **Fail closed / safe.** Any unexpected input path that can't be validated → `sys.exit(0)` (let the tool call through). Only block when we're confident a rule is violated.
- **UTF-8 stderr.** Already handled by `_lib/__init__.py`; don't undo it.
- **No third-party runtime dependencies.** Dev-only deps are fine.
- **Tests live in `tests/`** with the naming convention `test_<surface>.py`. Use the fixtures in `tests/conftest.py` for profile scaffolding and hook invocation.

## Commit messages

Short imperative mood. Prefix with a scope if it narrows the change:

```
hooks: accept Japanese slugs under default config
lib: extract glob_to_regex to _lib/patterns.py
docs: fix broken link in concepts.md
```

Larger changes should include a one-paragraph body explaining the *why*.

## Pull request checklist

Before you open a PR, make sure:

- [ ] Branch is up to date with `main`
- [ ] `pytest` passes
- [ ] `ruff check` passes
- [ ] `mypy` passes (or you've documented why new issues are unavoidable)
- [ ] Updated `CHANGELOG.md` under `## [Unreleased]`
- [ ] Updated relevant docs (README, docs/*.md, schema, or profile files)
- [ ] If you touched `memex_docsite/`: ran `memex-docsite --cwd examples/research-wiki-demo check` (catches Jinja regressions and broken-link drift)

## Reviewing culture

We aim for:

- **Direct feedback.** If a change needs rework, we'll say so clearly.
- **Fast turnaround.** Expect an initial response within a few working days.
- **Boring wins.** Small, focused, well-tested changes merge faster than sprawling refactors.

## Licence

By contributing, you agree that your contributions are licensed under the [MIT Licence](LICENSE) (same as the rest of the repo).
