FROM python:3.12-slim AS build-stage
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md /app/
COPY ./resslab_hub /app/resslab_hub
RUN uv pip install --no-deps . \
    && test -d /app/.venv/lib/python3.12/site-packages/resslab_hub


FROM python:3.12-slim AS production-stage
WORKDIR /app

COPY --from=build-stage /app/.venv /app/.venv
COPY ./alembic.ini /app/
COPY ./alembic /app/alembic
COPY ./data /app/data

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

ENTRYPOINT [ "python", "-m", "data.uploader" ]
