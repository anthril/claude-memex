# memex-docsite — self-hosted browsable wiki with optional live writes.
#
# Build:
#   docker build -t claude-memex-docsite .
#
# Run (read-only, no auth, mounts a host wiki at /wiki):
#   docker run --rm -p 8000:8000 \
#     -v $(pwd):/wiki \
#     claude-memex-docsite
#
# Run (token mode + writes enabled — production-ish):
#   docker run --rm -p 8000:8000 \
#     -e MEMEX_DOCSITE_TOKEN=$(openssl rand -hex 32) \
#     -v $(pwd):/wiki \
#     claude-memex-docsite \
#     memex-docsite serve --host 0.0.0.0 --auth token
#
# The image binds to 0.0.0.0 by default (only useful inside a container);
# put it behind Tailscale, Cloudflare Access, or nginx to expose safely.

FROM python:3.12-slim AS base

# Don't write .pyc files inside the container; flush stdout immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies separately so Docker layer-caches the install layer.
WORKDIR /opt/claude-memex
COPY pyproject.toml README.md LICENSE /opt/claude-memex/
COPY memex_docsite /opt/claude-memex/memex_docsite
COPY hooks /opt/claude-memex/hooks
COPY templates /opt/claude-memex/templates
COPY schemas /opt/claude-memex/schemas
COPY commands /opt/claude-memex/commands
COPY agents /opt/claude-memex/agents
COPY skills /opt/claude-memex/skills

RUN pip install --no-cache-dir ".[docsite]"

# Non-root runtime user. The mounted wiki at /wiki must be writable by uid=1000.
RUN groupadd -g 1000 memex && useradd -u 1000 -g 1000 -m -s /bin/bash memex
USER memex
WORKDIR /wiki

EXPOSE 8000

# Health probe for orchestrators.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"

# Default command — read-only viewer bound to all interfaces. Override
# with `docker run … memex-docsite serve --auth token` for writes.
CMD ["memex-docsite", "serve", "--host", "0.0.0.0", "--port", "8000"]
