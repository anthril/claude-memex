# memex-docsite Docker / self-host guide

A self-contained image that runs the docsite with live writes enabled,
mounts a wiki from the host filesystem, and exposes a single HTTP port.

## TL;DR

```bash
# 1) Build the image once.
docker build -t claude-memex-docsite .

# 2) Run a read-only viewer for a wiki on the host.
docker run --rm -p 8000:8000 -v $(pwd):/wiki claude-memex-docsite

# 3) Or production-ish — token mode + writes:
docker run --rm -p 8000:8000 \
  -e MEMEX_DOCSITE_TOKEN=$(openssl rand -hex 32) \
  -v $(pwd):/wiki \
  claude-memex-docsite \
  memex-docsite serve --host 0.0.0.0 --auth token
```

The mounted `/wiki` directory must contain a `memex.config.json` and
`.memex/` tree — the same layout `memex-docsite serve` would walk
locally. The container reads + writes inside `/wiki` so wiki changes
land back on the host filesystem and remain git-trackable.

## docker-compose

A ready-to-customise [`docker-compose.yml`](../docker-compose.yml) ships
in the repo root. Drop a `.env` next to it with:

```env
MEMEX_DOCSITE_TOKEN=<long random secret>     # `openssl rand -hex 32`
MEMEX_WIKI_PATH=/abs/path/to/your/wiki       # the project root with memex.config.json
MEMEX_DOCSITE_USER=alice                     # optional — name used as the `author` on submissions
```

Then:

```bash
docker compose up -d
```

The compose file:

- pins `--auth token` so writes require the bearer token,
- mounts the wiki rw,
- exposes 8000 on the host,
- runs the built-in `/api/health` healthcheck,
- restarts on failure.

## Reverse-proxy snippets

The image binds to `0.0.0.0` because it expects to live behind a
reverse proxy that terminates TLS + (optionally) provides identity.

### nginx

```nginx
server {
  listen 443 ssl http2;
  server_name wiki.example.com;
  # ssl_certificate / ssl_certificate_key …

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    # If you authenticate users via auth_request and set their identity:
    # proxy_set_header X-Forwarded-User $authenticated_user;
  }
}
```

If the proxy authenticates users (e.g., basic-auth, OIDC via
`auth_request`, Cloudflare Access, Tailscale Funnel), set
`docsite.auth = "proxy"` in `memex.config.json` instead of `token`.
The docsite then trusts `X-Forwarded-User` as the submission `author`.

### Caddy

```caddyfile
wiki.example.com {
    reverse_proxy 127.0.0.1:8000
    # If using forward-auth:
    # forward_auth auth.example.com {
    #   uri /verify
    #   copy_headers X-Forwarded-User
    # }
}
```

### Traefik (compose label)

Adding a Traefik label set to the compose service:

```yaml
services:
  docsite:
    # …rest of compose service…
    labels:
      - traefik.enable=true
      - traefik.http.routers.docsite.rule=Host(`wiki.example.com`)
      - traefik.http.routers.docsite.entrypoints=websecure
      - traefik.http.routers.docsite.tls.certresolver=letsencrypt
      - traefik.http.services.docsite.loadbalancer.server.port=8000
```

### Tailscale (sidecar pattern)

```yaml
services:
  ts:
    image: tailscale/tailscale:latest
    cap_add: [net_admin, sys_module]
    volumes:
      - /var/lib/tailscale:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun
    environment:
      TS_AUTHKEY: ${TS_AUTHKEY:?}
      TS_HOSTNAME: docsite
      TS_USERSPACE: "false"
  docsite:
    image: claude-memex-docsite:latest
    network_mode: service:ts
    # …rest of service…
```

This binds the docsite to your tailnet only — no public exposure. For
identity-aware deployment, run the docsite behind Tailscale Serve and
have the proxy inject `X-Forwarded-User`; pair with
`docsite.auth = "proxy"`.

## Persistence

All wiki writes (open questions, rules, comments, annotations) live
inside `<wiki>/.memex/{.open-questions,.rules,.comments,.annotations}/`.
Volumes that survive container recreation are sufficient — no external
database, no Redis, no Postgres. To back up, snapshot the wiki dir
(it's plain markdown + JSONL).

## Updating

The image bakes the plugin source at build time. To upgrade:

```bash
docker compose pull         # if pushed to a registry
# OR
docker compose build --pull # local rebuild
docker compose up -d
```

No data migration is needed — the on-disk format is stable across
patch versions.

## File ownership

The image runs as `uid=1000`, `gid=1000` (`memex` user). If your
mounted wiki is owned by a different uid, either:

- chown it on the host (`sudo chown -R 1000:1000 /path/to/wiki`), or
- override at runtime (`docker run --user $(id -u):$(id -g) …`).

The default user keeps the container from writing files as root if
the volume mount is root-owned by accident.

## Hardening checklist

| Concern                     | Mitigation                                                        |
| --------------------------- | ----------------------------------------------------------------- |
| Token theft                 | Use HTTPS only; rotate with `openssl rand -hex 32`; revoke by changing the env var. |
| CSRF                        | Writes go through `/api/...` and require `Authorization: Bearer …`. CORS isn't enabled — the docsite serves the form that submits to it on the same origin. |
| Path traversal              | Page-slug sanitiser blocks `..` and disallowed characters per segment (covered by tests). |
| Container escape            | Runs as non-root uid 1000; only `/wiki` is writable.              |
| Resource exhaustion         | Body size cap on comments (8 KB); annotation body has no explicit cap but the file write goes through the standard frontmatter validator. |
| Image base CVEs             | Rebuild on `python:3.12-slim` updates; `docker compose pull` or rebuild monthly. |

## Verifying a deployment

```bash
curl -s http://localhost:8000/api/health           # → {"status":"ok"}
curl -s http://localhost:8000/api/graph | jq .summary
curl -s http://localhost:8000/api/comments/index   # public-visibility comments
```

A 200 from `/api/health` and a real graph payload means the wiki
mount, port forwarding, and Python deps are all wired correctly.
