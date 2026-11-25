FROM python:3.12-slim AS build-stage
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
# uv needs git to fetch enacit4r-contrib, a git dependency. The build stage
# only: the production stage copies the venv, not git.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Layer 1 — deps only (re-uses cache unless pyproject.toml / uv.lock change)
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

# Layer 2 — project (re-uses cache unless source changes)
COPY README.md /app/
COPY ./resslab_hub /app/resslab_hub
RUN uv pip install --no-deps . \
    && test -d /app/.venv/lib/python3.12/site-packages/resslab_hub


FROM python:3.12-slim AS production-stage
EXPOSE 80
WORKDIR /app

COPY --from=build-stage /app/.venv /app/.venv
COPY ./alembic.ini /app/
COPY ./alembic /app/alembic

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

CMD [ "uvicorn", "resslab_hub.main:app", "--host", "0.0.0.0", "--port", "80" ]
