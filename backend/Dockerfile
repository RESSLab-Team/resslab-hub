FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b AS build-stage
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1

# Layer 1 — deps only (re-uses cache unless pyproject.toml / uv.lock change)
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

# Layer 2 — project (re-uses cache unless source changes)
COPY README.md /app/
COPY ./resslab_hub /app/resslab_hub
RUN uv pip install --no-deps . \
    && test -d /app/.venv/lib/python3.12/site-packages/resslab_hub


FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b AS production-stage
EXPOSE 8080
WORKDIR /app

# The user that runs the app (#456). A fixed uid, so the k8s manifests can
# name it. It gets a home folder, so a library that writes a cache in ~ does
# not fail. /app stays owned by root: the app reads its code, it can't change it.
RUN useradd --system --uid 10001 --create-home appuser

COPY --from=build-stage /app/.venv /app/.venv
COPY ./alembic.ini /app/
COPY ./alembic /app/alembic

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# By number, not by name: k8s can only check runAsNonRoot on a numeric user.
# Not root, so no port under 1024: the app listens on 8080.
USER 10001:10001

CMD [ "uvicorn", "resslab_hub.main:app", "--host", "0.0.0.0", "--port", "8080" ]
