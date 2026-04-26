"""memex_docsite — the optional docsite layer for claude-memex.

Renders a memex wiki as a browsable HTML site with optional live writes
(open questions, rules, comments, annotations) and a static-export mode
for read-only public hosting. Hooks remain stdlib-only; this package is
an optional dependency group (`pip install claude-memex[docsite]`).

Note: deliberately no `from __future__ import annotations` here — the
package contains a submodule literally called `annotations.py`, and the
future-flag would bind the name `annotations` in this namespace to a
`_Feature` object, shadowing the submodule.
"""

__all__ = ["__version__"]
__version__ = "0.1.0a1"
