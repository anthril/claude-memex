# mock_qmd

A stub `qmd` binary used by `test_hooks_session.py::TestUserPromptContext::test_qmd_integration_with_mock_binary`.

The real file is generated on-the-fly by the test when it runs (so we don't commit a platform-specific shell script). The test binary emits a fixed JSON payload pointing at a known page; the hook must parse it and surface the page in the context output.

If you want to wire in the real qmd, install it (`cargo install qmd` or grab a binary from https://github.com/tobi/qmd), set `"search": {"engine": "qmd"}` in your project's `memex.config.json`, then run `qmd index` once against your `.memex/` tree to build the initial index.
