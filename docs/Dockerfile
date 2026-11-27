# The docs site as its own image: Zensical builds it, nginx serves it under
# /docs/ (the ingress of each hub sends /docs there). Built by deploy.yml from
# this folder alone, like backend/ and frontend/. CI builds it on each pull
# request, so a warning or a dead link fails there.

# Stage 1: build the site
FROM python:3.13-slim@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50 AS build-stage
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: deps only (re-used unless pyproject.toml or uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Layer 2: the data repo, for the "Databases" pages. The feed changes when its
# main branch moves, so the clone below is not taken from the build cache.
# Without blobs: the script reads the few files it needs with `git show`.
ADD https://github.com/RESSLab-Team/resslab-hub-data/commits/main.atom /tmp/data-repo-head
RUN git clone --quiet --depth 1 --filter=blob:none --no-checkout \
    https://github.com/RESSLab-Team/resslab-hub-data /data-repo

# Layer 3: the pages. Same steps as `make docs`.
COPY . .
RUN python scripts/data-repo.py /data-repo HEAD \
    && uv run --no-sync zensical build --clean --strict \
    && python scripts/data-repo.py --edit-links site \
    && python scripts/check-links.py site \
    && python scripts/check-orphans.py

# Stage 2: serve it. The unprivileged image listens on 8080.
FROM nginxinc/nginx-unprivileged:stable-alpine-slim@sha256:5d8bb9437d74a600ec5dbf90c035451c724dc33eac8d3a71078f6f8612c345f6 AS production-stage
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-stage /app/site /usr/share/nginx/html/docs
EXPOSE 8080
