"""`memex-docsite` CLI — `serve | build | check`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, config


def _cmd_serve(args: argparse.Namespace) -> int:
    cfg = config.load(start=Path(args.cwd) if args.cwd else None)
    if not cfg.enabled:
        print("docsite is disabled in memex.config.json (set docsite.enabled = true)", file=sys.stderr)
        return 1
    if args.port:
        cfg.port = args.port
    if args.host:
        cfg.host = args.host
    if args.auth:
        cfg.auth = args.auth
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - install-time guard
        print(
            "uvicorn is missing. Install the docsite extras: `pip install claude-memex[docsite]`",
            file=sys.stderr,
        )
        return 2

    from .server import make_app

    app = make_app(cfg)
    print(f"memex-docsite serving {cfg.wiki_root} at http://{cfg.host}:{cfg.port}")
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    cfg = config.load(start=Path(args.cwd) if args.cwd else None)
    from .exporter import export

    out = Path(args.out).resolve() if args.out else None
    result = export(cfg, out_dir=out)
    final_out = out or (cfg.project_root / cfg.export_path).resolve()
    print(
        f"static export complete -> {final_out}\n"
        f"  pages: {result.pages_written}\n"
        f"  folder indexes: {result.folders_written}\n"
        f"  list pages: {result.list_pages_written}\n"
        f"  assets: {result.assets_copied}"
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    cfg = config.load(start=Path(args.cwd) if args.cwd else None)
    # Render to a tmp dir to surface broken links + render errors.
    import tempfile

    from .exporter import export

    with tempfile.TemporaryDirectory() as tmp:
        result = export(cfg, out_dir=Path(tmp))
    print(f"check ok - {result.pages_written} page(s) rendered, {result.folders_written} folder index(es)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memex-docsite", description=__doc__)
    parser.add_argument("--version", action="version", version=f"memex-docsite {__version__}")
    parser.add_argument("--cwd", default=None, help="Start config discovery from this directory.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="Run the dev server.")
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("--auth", choices=("none", "token", "proxy"), default=None)
    p_serve.set_defaults(func=_cmd_serve)

    p_build = sub.add_parser("build", help="Static export.")
    p_build.add_argument("--out", default=None, help="Output directory (default: docsite.exportPath).")
    p_build.set_defaults(func=_cmd_build)

    p_check = sub.add_parser("check", help="Validate config and surface broken links / render errors.")
    p_check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
