FROM python:3.10-alpine as build-stage
WORKDIR /app
RUN apk add --no-cache \
    gcc \
    musl-dev
RUN pip install poetry
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry export --output requirements.txt


FROM python:3.10-alpine as production-stage
EXPOSE 80
WORKDIR /app
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev

COPY --from=build-stage /app/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY ./alembic.ini /app/
COPY ./alembic /app/alembic
COPY ./resslab_hub /app/resslab_hub

CMD [ "uvicorn", "resslab_hub.main:app", "--host", "0.0.0.0", "--port", "80" ]
