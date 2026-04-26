"""Docsite-specific config — reads the `docsite` block from `memex.config.json`.

The block is optional; absent fields fall back to documented defaults so a
project that never opted into the docsite still gets a usable read-only
viewer when `memex-docsite serve` is run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .paths import find_project_root, load_raw_config, wiki_root

AuthMode = Literal["none", "token", "proxy"]
ThemeMode = Literal["auto", "light", "dark"]
WriteFeature = Literal["open-questions", "rules", "comments", "annotations"]


@dataclass(slots=True)
class AnnotationConfig:
    default_visibility: Literal["public", "group", "private"] = "public"
    allow_anonymous: bool = True
    indexable: bool = False


@dataclass(slots=True)
class DocsiteConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    auth: AuthMode = "none"
    title: str = "Memex wiki"
    theme: ThemeMode = "auto"
    show_hidden: bool = True
    write_features: list[WriteFeature] = field(default_factory=list)
    export_path: str = "dist/"
    ignore_patterns: list[str] = field(default_factory=list)
    annotations: AnnotationConfig = field(default_factory=AnnotationConfig)

    project_root: Path = field(default=Path("."))
    wiki_root: Path = field(default=Path("."))
    memex_root: Path = field(default=Path("."))
    raw_config: dict = field(default_factory=dict)

    # Profile-derived nav inputs. Populated from `index.sections` and
    # `frontmatter.enum.type` so the docsite can render a section-driven
    # sidebar without re-parsing the raw config in every template.
    index_sections: list = field(default_factory=list)
    type_enum: list[str] = field(default_factory=list)
    enum_display_names: dict = field(default_factory=dict)

    def is_ignored(self, rel_path: str) -> bool:
        """Match a path (POSIX, relative to wiki_root) against ignorePatterns."""
        if not self.ignore_patterns:
            return False
        from fnmatch import fnmatch

        for pat in self.ignore_patterns:
            if fnmatch(rel_path, pat):
                return True
            # Also allow patterns to match any path *segment* — `node_modules/**`
            # against `foo/node_modules/bar/baz` should hit too.
            for i in range(len(rel_path)):
                if rel_path[i] == "/" and fnmatch(rel_path[i + 1 :], pat):
                    return True
        return False

    @property
    def static_mode(self) -> bool:
        """True when running `build` (no live writes)."""
        return False

    def write_enabled(self, feature: WriteFeature) -> bool:
        return self.enabled and not self.static_mode and feature in self.write_features


# Patterns the docsite always ignores even if the user doesn't list them.
# `.state/sessions/**` are PreCompact session snapshots written by the hook
# bus and are noise in the docsite's nav. Explicit user patterns are merged
# on top so a project can still un-ignore them with care.
_DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".state/sessions/**",
)


def _with_default_ignores(user_patterns: list[str]) -> list[str]:
    out = list(_DEFAULT_IGNORE_PATTERNS)
    for p in user_patterns:
        if p not in out:
            out.append(p)
    return out


def _coerce(raw: dict | None, key: str, default, expected_type=None):
    """Read a key from a dict and validate its type, falling back to default."""
    if raw is None or key not in raw:
        return default
    val = raw[key]
    if expected_type is not None and not isinstance(val, expected_type):
        raise ValueError(
            f"docsite.{key} must be {expected_type.__name__}, got {type(val).__name__}"
        )
    return val


def load(start: Path | None = None) -> DocsiteConfig:
    """Locate the project, read `memex.config.json`, build a DocsiteConfig."""
    root = find_project_root(start)
    raw = load_raw_config(root)
    docsite_raw = raw.get("docsite") or {}

    annotations_raw = docsite_raw.get("annotations") or {}
    annotations = AnnotationConfig(
        default_visibility=_coerce(annotations_raw, "defaultVisibility", "public", str),
        allow_anonymous=_coerce(annotations_raw, "allowAnonymous", True, bool),
        indexable=_coerce(annotations_raw, "indexable", False, bool),
    )

    # The canonical memex root — always `.memex/` per the raw config. All
    # docsite writes (open-questions, rules, annotations, comments) land
    # here regardless of how wide `contentRoot` reaches for reads.
    canonical_memex = wiki_root(root, raw)

    # docsite.contentRoot lets a project surface a wider tree than `.memex/`
    # without disturbing the hook contract (hooks keep reading `cfg["root"]`
    # from the raw JSON). Default: the canonical `.memex/` wiki root.
    content_override = docsite_raw.get("contentRoot")
    if content_override:
        if not isinstance(content_override, str):
            raise ValueError("docsite.contentRoot must be a string path")
        effective_root = (root / content_override).resolve()
    else:
        effective_root = canonical_memex

    index_raw = raw.get("index") or {}
    index_sections = list(index_raw.get("sections") or [])

    fm_raw = raw.get("frontmatter") or {}
    type_enum = list((fm_raw.get("enum") or {}).get("type") or [])
    enum_display_names = dict(fm_raw.get("enumDisplayNames") or {})

    cfg = DocsiteConfig(
        enabled=_coerce(docsite_raw, "enabled", True, bool),
        host=_coerce(docsite_raw, "host", "127.0.0.1", str),
        port=_coerce(docsite_raw, "port", 8000, int),
        auth=_coerce(docsite_raw, "auth", "none", str),
        title=_coerce(docsite_raw, "title", _default_title(raw), str),
        theme=_coerce(docsite_raw, "theme", "auto", str),
        show_hidden=_coerce(docsite_raw, "showHidden", True, bool),
        write_features=list(_coerce(docsite_raw, "writeFeatures", [], list)),
        export_path=_coerce(docsite_raw, "exportPath", "dist/", str),
        ignore_patterns=_with_default_ignores(
            list(_coerce(docsite_raw, "ignorePatterns", [], list))
        ),
        annotations=annotations,
        project_root=root,
        wiki_root=effective_root,
        memex_root=canonical_memex,
        raw_config=raw,
        index_sections=index_sections,
        type_enum=type_enum,
        enum_display_names=enum_display_names,
    )

    if cfg.auth not in ("none", "token", "proxy"):
        raise ValueError(f"docsite.auth must be one of none|token|proxy, got {cfg.auth!r}")

    return cfg


def _default_title(raw: dict) -> str:
    """Derive a reasonable default title from the project's profile + root."""
    profile = raw.get("profile", "wiki")
    return f"{profile.replace('-', ' ').title()} — Memex"
