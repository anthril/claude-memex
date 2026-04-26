"""Starlette app — Phase 1 routes (read-only viewer).

Phase 1 surfaces:
- GET /                     index page
- GET /<path>               render a markdown file as HTML
- GET /<folder>/            folder index (auto-generated when no index.md exists)
- GET /static/<path>        bundled CSS/JS/fonts
- GET /raw/<path>           serve raw assets (PDFs, images, transcripts)
- GET /api/health           liveness probe

Later phases extend this app with /search, /graph, /open-questions, /rules,
/api/annotations, /api/comments. The application factory below is the only
entry point — phase modules attach their routes to the same `Starlette` instance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import annotations as annotations_module
from . import auth as auth_module
from . import comments as comments_module
from . import graph as graph_module
from . import renderer, resolver, search, sitetree, submissions
from .config import DocsiteConfig

PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def _redirect_after_post(url: str) -> RedirectResponse:
    """303 — POST handlers return this so refresh doesn't repost."""
    return RedirectResponse(url=url, status_code=303)


def _open_questions_list_response(cfg: DocsiteConfig, env: Environment) -> HTMLResponse:
    items = submissions.list_open_questions(cfg)
    active = [i for i in items if not i["resolved"]]
    resolved = [i for i in items if i["resolved"]]
    return _render_template(
        env,
        "open-questions/list.html",
        active=active,
        resolved=resolved,
        current_slug="open-questions",
        write_enabled=cfg.write_enabled("open-questions"),
        breadcrumbs=_breadcrumbs("open-questions"),
        backlinks=[],
        **_shared_context(cfg),
    )


def _rules_list_response(cfg: DocsiteConfig, env: Environment) -> HTMLResponse:
    items = submissions.list_rules(cfg)
    return _render_template(
        env,
        "rules/list.html",
        rules=items,
        current_slug="rules",
        write_enabled=cfg.write_enabled("rules"),
        breadcrumbs=_breadcrumbs("rules"),
        backlinks=[],
        **_shared_context(cfg),
    )


def _comments_overview_response(
    cfg: DocsiteConfig, env: Environment, *, viewer_name: str = "anonymous", is_authenticated: bool = False
) -> HTMLResponse:
    records = comments_module.list_recent_across_pages(
        cfg,
        viewer_name=viewer_name,
        is_authenticated=is_authenticated,
        limit=50,
    )
    return _render_template(
        env,
        "comments/list.html",
        recent=records,
        current_slug="comments",
        breadcrumbs=_breadcrumbs("comments"),
        backlinks=[],
        **_shared_context(cfg),
    )


def _breadcrumbs(slug: str) -> list[dict]:
    """Derive a list of (label, url) crumbs from a slug.

    `architecture/engineering-spec/01-event-substrate` becomes
    [{Home, /}, {Architecture, /architecture/}, {Engineering Spec, /architecture/engineering-spec/}].
    The current page itself is omitted — the page header already shows it.
    """
    crumbs: list[dict] = [{"label": "Home", "url": "/"}]
    if not slug or slug == "index":
        return crumbs
    parts = slug.strip("/").split("/")
    for depth in range(len(parts) - 1):
        sub = "/".join(parts[: depth + 1])
        label = parts[depth].replace("-", " ").replace("_", " ").title()
        crumbs.append({"label": label, "url": f"/{sub}/"})
    return crumbs


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["slug_to_url"] = resolver.slug_to_url
    return env


def _render_template(env: Environment, name: str, **ctx: Any) -> HTMLResponse:
    template = env.get_template(name)
    return HTMLResponse(template.render(**ctx))


def _shared_context(cfg: DocsiteConfig) -> dict[str, Any]:
    tree = sitetree.build(
        cfg.wiki_root, show_hidden=cfg.show_hidden, is_ignored=cfg.is_ignored
    )
    search_engine = (cfg.raw_config.get("search") or {}).get("engine", "grep")
    return {
        "site_title": cfg.title,
        "theme": cfg.theme,
        "auth_mode": cfg.auth,
        "static_mode": cfg.static_mode,
        "write_features": list(cfg.write_features),
        "tree": tree,
        "search_engine": search_engine,
    }


def _page_response(
    cfg: DocsiteConfig,
    env: Environment,
    slug: str,
    *,
    graph: graph_module.Graph | None = None,
) -> HTMLResponse:
    if cfg.is_ignored(slug + ".md") or cfg.is_ignored(slug + "/"):
        raise HTTPException(404)
    file_path = resolver.slug_to_path(slug, cfg.wiki_root)
    if file_path is None:
        # Maybe it's a folder route → render folder index.
        folder = (cfg.wiki_root / slug).resolve()
        try:
            folder.relative_to(cfg.wiki_root.resolve())
        except ValueError:
            folder = None  # type: ignore[assignment]
        if folder and folder.is_dir() and not cfg.is_ignored(slug + "/"):
            return _folder_response(cfg, env, slug, folder)
        raise HTTPException(404)

    content = file_path.read_text(encoding="utf-8", errors="replace")
    page = renderer.render(content, slug, cfg.wiki_root)
    backlinks = (
        [
            {"slug": n.slug, "title": n.title, "url": resolver.slug_to_url(n.slug)}
            for n in graph_module.backlinks_for(graph, slug)
        ]
        if graph is not None
        else []
    )
    return _render_template(
        env,
        "page.html",
        page=page,
        current_slug=slug,
        breadcrumbs=_breadcrumbs(slug),
        backlinks=backlinks,
        **_shared_context(cfg),
    )


def _folder_response(cfg: DocsiteConfig, env: Environment, slug: str, folder: Path) -> HTMLResponse:
    children = []
    for path in sorted(folder.iterdir(), key=lambda p: (p.is_dir(), p.name.lower())):
        if path.name.startswith(".") and not cfg.show_hidden:
            continue
        if path.is_dir():
            children.append(
                {
                    "name": path.name,
                    "url": resolver.slug_to_url(f"{slug}/{path.name}".strip("/")),
                    "is_folder": True,
                }
            )
        elif path.suffix == ".md":
            child_slug = resolver.path_to_slug(path, cfg.wiki_root)
            children.append(
                {
                    "name": path.name,
                    "url": resolver.slug_to_url(child_slug),
                    "is_folder": False,
                }
            )
    return _render_template(
        env,
        "folder.html",
        folder_name=slug or "/",
        slug=slug,
        children=children,
        current_slug=slug,
        breadcrumbs=_breadcrumbs(slug),
        backlinks=[],
        **_shared_context(cfg),
    )


# ─── route handlers ────────────────────────────────────────────────────────────


_GRAPH_TTL_SECONDS = 5.0


def make_app(cfg: DocsiteConfig) -> Starlette:
    env = _make_env()
    # Per-app graph cache — saves rebuilding the link graph on every page
    # render. `time.monotonic` is used so a system clock change can't poison
    # the cache.
    import time

    graph_cache = {"at": -1.0, "graph": None}

    def cached_graph():
        now = time.monotonic()
        if (
            graph_cache["graph"] is None
            or now - graph_cache["at"] > _GRAPH_TTL_SECONDS
        ):
            graph_cache["graph"] = graph_module.build(
                cfg.wiki_root, show_hidden=cfg.show_hidden, is_ignored=cfg.is_ignored
            )
            graph_cache["at"] = now
        return graph_cache["graph"]

    async def index(request: Request) -> Response:
        return _page_response(cfg, env, "index", graph=cached_graph())

    async def page(request: Request) -> Response:
        slug = request.path_params["slug"].strip("/")
        if not slug:
            return _page_response(cfg, env, "index", graph=cached_graph())
        return _page_response(cfg, env, slug, graph=cached_graph())

    async def raw_asset(request: Request) -> Response:
        relpath = request.path_params["path"]
        candidate = (cfg.wiki_root / "raw" / relpath).resolve()
        try:
            candidate.relative_to((cfg.wiki_root / "raw").resolve())
        except ValueError as exc:
            raise HTTPException(404) from exc
        if not candidate.is_file():
            raise HTTPException(404)
        return FileResponse(candidate)

    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    async def search_route(request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        engine = (cfg.raw_config.get("search") or {}).get("engine", "grep")
        results = (
            search.search(
                query,
                cfg.wiki_root,
                top_n=int(request.query_params.get("n") or 20),
                engine=engine,
                show_hidden=cfg.show_hidden,
                is_ignored=cfg.is_ignored,
            )
            if query
            else []
        )
        return _render_template(
            env,
            "search-results.html",
            query=query,
            results=results,
            current_slug="search",
            **_shared_context(cfg),
        )

    async def graph_route(request: Request) -> Response:
        return _render_template(
            env,
            "graph.html",
            current_slug="graph",
            **_shared_context(cfg),
        )

    async def graph_json(request: Request) -> Response:
        return JSONResponse(graph_module.to_dict(cached_graph()))

    # ─── Phase 3: open-questions + rules submission ──────────────────────────

    async def open_questions_list(request: Request) -> Response:
        return _open_questions_list_response(cfg, env)

    async def open_questions_form(request: Request) -> Response:
        if not cfg.write_enabled("open-questions"):
            raise HTTPException(404)
        return _render_template(
            env,
            "open-questions/form.html",
            current_slug="open-questions",
            error=None,
            values={},
            **_shared_context(cfg),
        )

    async def open_questions_submit(request: Request) -> Response:
        if not cfg.write_enabled("open-questions"):
            raise HTTPException(404)
        form = dict(await request.form())
        try:
            identity = auth_module.require_write_identity(request, cfg, form=form)
        except HTTPException:
            raise
        title = (form.get("title") or "").strip()
        body = (form.get("body") or "").strip()
        if not title or not body:
            return _render_template(
                env,
                "open-questions/form.html",
                error="Title and body are required.",
                values=form,
                current_slug="open-questions",
                    **_shared_context(cfg),
            )
        try:
            result = submissions.submit_open_question(
                cfg,
                title=title,
                body=body,
                author=identity.name,
                owner=form.get("owner") or None,
                related=form.get("related") or None,
            )
        except ValueError as exc:
            return _render_template(
                env,
                "open-questions/form.html",
                error=str(exc),
                values=form,
                current_slug="open-questions",
                    **_shared_context(cfg),
            )
        return _redirect_after_post(f"/open-questions/{result.slug}")

    async def open_questions_resolve(request: Request) -> Response:
        if not cfg.write_enabled("open-questions"):
            raise HTTPException(404)
        slug = request.path_params["slug"]
        form = dict(await request.form())
        identity = auth_module.require_write_identity(request, cfg, form=form)
        try:
            submissions.resolve_open_question(cfg, slug, resolver=identity.name)
        except FileNotFoundError as exc:
            raise HTTPException(404) from exc
        return _redirect_after_post("/open-questions")

    async def rules_list(request: Request) -> Response:
        return _rules_list_response(cfg, env)

    async def rules_form(request: Request) -> Response:
        if not cfg.write_enabled("rules"):
            raise HTTPException(404)
        return _render_template(
            env,
            "rules/form.html",
            current_slug="rules",
            error=None,
            values={},
            **_shared_context(cfg),
        )

    async def rules_submit(request: Request) -> Response:
        if not cfg.write_enabled("rules"):
            raise HTTPException(404)
        form = dict(await request.form())
        identity = auth_module.require_write_identity(request, cfg, form=form)
        title = (form.get("title") or "").strip()
        body = (form.get("body") or "").strip()
        if not title or not body:
            return _render_template(
                env,
                "rules/form.html",
                error="Title and body are required.",
                values=form,
                current_slug="rules",
                    **_shared_context(cfg),
            )
        try:
            result = submissions.submit_rule(
                cfg,
                title=title,
                body=body,
                author=identity.name,
                owner=form.get("owner") or None,
                scope=form.get("scope") or None,
            )
        except ValueError as exc:
            return _render_template(
                env,
                "rules/form.html",
                error=str(exc),
                values=form,
                current_slug="rules",
                **_shared_context(cfg),
            )
        return _redirect_after_post(f"/{submissions.RULES_DIR}/{result.slug}")

    # ─── Phase 4: inline annotations ─────────────────────────────────────────

    def _annotation_payload(rec: dict) -> dict:
        """Trim the on-disk record to a JSON-friendly shape for the API."""
        return {
            "id": rec.get("id"),
            "author": rec.get("author"),
            "visibility": rec.get("visibility"),
            "created": rec.get("created"),
            "updated": rec.get("updated"),
            "status": rec.get("status"),
            "selector": rec.get("selector"),
            "position": rec.get("position"),
            "replies_to": rec.get("replies_to"),
            "body": rec.get("body", ""),
        }

    async def annotations_list(request: Request) -> Response:
        page_slug = request.path_params["page_slug"]
        identity = auth_module.identify(request, cfg, form=None)
        try:
            records = annotations_module.list_annotations(
                cfg,
                page_slug,
                viewer_name=identity.name,
                is_authenticated=not identity.is_anonymous,
            )
        except annotations_module.AnnotationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse([_annotation_payload(r) for r in records])

    async def annotations_create(request: Request) -> Response:
        if not cfg.write_enabled("annotations"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            result = annotations_module.create_annotation(
                cfg,
                page_slug,
                body=payload.get("body") or "",
                selector=payload.get("selector"),
                position=payload.get("position"),
                author=identity.name,
                visibility=payload.get("visibility"),
                replies_to=payload.get("replies_to"),
            )
        except annotations_module.AnnotationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(_annotation_payload(result.record), status_code=201)

    async def annotations_update(request: Request) -> Response:
        if not cfg.write_enabled("annotations"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        ann_id = request.path_params["ann_id"]
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            result = annotations_module.update_annotation(
                cfg,
                page_slug,
                ann_id,
                body=payload.get("body"),
                visibility=payload.get("visibility"),
                author=identity.name,
                is_authenticated=not identity.is_anonymous,
            )
        except annotations_module.AnnotationError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse(_annotation_payload(result.record))

    async def annotations_delete(request: Request) -> Response:
        if not cfg.write_enabled("annotations"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        ann_id = request.path_params["ann_id"]
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            annotations_module.delete_annotation(
                cfg,
                page_slug,
                ann_id,
                author=identity.name,
                is_authenticated=not identity.is_anonymous,
            )
        except annotations_module.AnnotationError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse({"status": "deleted"})

    # ─── Phase 5: page-level comments ────────────────────────────────────────

    async def comments_overview(request: Request) -> Response:
        identity = auth_module.identify(request, cfg, form=None)
        return _comments_overview_response(
            cfg, env,
            viewer_name=identity.name,
            is_authenticated=not identity.is_anonymous,
        )

    async def comments_list(request: Request) -> Response:
        page_slug = request.path_params["page_slug"]
        identity = auth_module.identify(request, cfg, form=None)
        try:
            records = comments_module.list_comments(
                cfg,
                page_slug,
                viewer_name=identity.name,
                is_authenticated=not identity.is_anonymous,
            )
        except comments_module.CommentError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(records)

    async def comments_create(request: Request) -> Response:
        if not cfg.write_enabled("comments"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            record = comments_module.add_comment(
                cfg,
                page_slug,
                body=payload.get("body") or "",
                author=identity.name,
                visibility=payload.get("visibility"),
                replies_to=payload.get("replies_to"),
            )
        except comments_module.CommentError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse(record, status_code=201)

    async def comments_update(request: Request) -> Response:
        if not cfg.write_enabled("comments"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        comment_id = request.path_params["comment_id"]
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            record = comments_module.update_comment(
                cfg,
                page_slug,
                comment_id,
                body=payload.get("body"),
                visibility=payload.get("visibility"),
                author=identity.name,
            )
        except comments_module.CommentError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse(record)

    async def comments_delete(request: Request) -> Response:
        if not cfg.write_enabled("comments"):
            raise HTTPException(404)
        page_slug = request.path_params["page_slug"]
        comment_id = request.path_params["comment_id"]
        try:
            identity = auth_module.require_write_identity(request, cfg)
        except HTTPException:
            raise
        try:
            comments_module.delete_comment(
                cfg, page_slug, comment_id, author=identity.name
            )
        except comments_module.CommentError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse({"status": "deleted"})

    async def not_found(request: Request, exc: HTTPException) -> Response:
        template = env.get_template("404.html")
        body = template.render(
            current_slug=request.url.path.lstrip("/"),
            **_shared_context(cfg),
        )
        return HTMLResponse(body, status_code=404)

    routes = [
        Route("/", index),
        Route("/search", search_route),
        Route("/graph", graph_route),
        Route("/api/health", health),
        Route("/api/graph", graph_json),
        # Phase 3 — open-questions
        Route("/open-questions", open_questions_list, methods=["GET"]),
        Route("/open-questions/new", open_questions_form, methods=["GET"]),
        Route("/open-questions", open_questions_submit, methods=["POST"]),
        Route(
            "/open-questions/{slug}/resolve",
            open_questions_resolve,
            methods=["POST"],
        ),
        # Phase 3 — rules
        Route("/rules", rules_list, methods=["GET"]),
        Route("/rules/new", rules_form, methods=["GET"]),
        Route("/rules", rules_submit, methods=["POST"]),
        # Phase 4 — annotations
        Route(
            "/api/annotations/{page_slug:path}/{ann_id}",
            annotations_update,
            methods=["PATCH"],
        ),
        Route(
            "/api/annotations/{page_slug:path}/{ann_id}",
            annotations_delete,
            methods=["DELETE"],
        ),
        Route(
            "/api/annotations/{page_slug:path}",
            annotations_list,
            methods=["GET"],
        ),
        Route(
            "/api/annotations/{page_slug:path}",
            annotations_create,
            methods=["POST"],
        ),
        # Phase 5 — comments
        Route("/comments", comments_overview, methods=["GET"]),
        Route(
            "/api/comments/{page_slug:path}/{comment_id}",
            comments_update,
            methods=["PATCH"],
        ),
        Route(
            "/api/comments/{page_slug:path}/{comment_id}",
            comments_delete,
            methods=["DELETE"],
        ),
        Route(
            "/api/comments/{page_slug:path}",
            comments_list,
            methods=["GET"],
        ),
        Route(
            "/api/comments/{page_slug:path}",
            comments_create,
            methods=["POST"],
        ),
        Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
        Route("/raw/{path:path}", raw_asset),
        Route("/{slug:path}", page),
    ]

    app = Starlette(
        debug=False,
        routes=routes,
        exception_handlers={404: not_found},
    )
    app.state.docsite_config = cfg
    return app
