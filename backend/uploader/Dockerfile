FROM python:3.10-alpine as build-stage
WORKDIR /app
RUN apk add --no-cache \
    gcc \
    musl-dev
RUN pip install poetry
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry export --output requirements.txt


FROM python:3.10-alpine as production-stage
WORKDIR /app
RUN apk add --no-cache \
    g++ \
    gcc \
    musl-dev \
    postgresql-dev

COPY --from=build-stage /app/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY ./alembic.ini ./pyproject.toml ./README.md /app/
COPY ./resslab_hub /app/resslab_hub
COPY ./alembic /app/alembic
COPY ./data /app/data

RUN pip install --no-cache-dir .

ENTRYPOINT [ "python", "-m", "data.uploader" ]
