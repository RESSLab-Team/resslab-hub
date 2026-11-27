"""
Routes for AI agents that prepare a submission for a researcher.

The researcher copies a prompt from the contribution form and gives it to
their own agent. The agent reads the guide, converts the researcher's files,
checks them with ``POST /agent/validate`` and gives back a folder, which the
researcher drops on the form and submits under their own name. The agent never
submits: these routes write nothing. See docs/src/contributing-data.md.

The check is open to anybody, without an account, so it is smaller than
``/validate``: 10 MB, 10 a minute per address, one at a time for the whole
process, and no call to GitHub.
"""

import asyncio
from enum import Enum
from os import path
from typing import Dict

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from resslab_hub.agent import guide
from resslab_hub.auth.deps import require_contributions_enabled
from resslab_hub.auth.urls import api_base, public_base
from resslab_hub.config import settings
from resslab_hub.models.api import DictionaryColumnModel
from resslab_hub.models.database.dictionary import DatabaseReadme, DictionaryColumn
from resslab_hub.models.validation import (
    FileValidationResult,
    ValidationIssue,
    ValidationReport,
)
from resslab_hub.routers.root import check_content_length, validate_upload
from resslab_hub.utils.caching import data_version
from resslab_hub.utils.database import get_session
from resslab_hub.utils.rate_limit import limiter

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(require_contributions_enabled)],
)

#: About 200 tests with three response files each (see MAX_REQUEST_BYTES).
MAX_AGENT_BYTES = 10 * 2**20

#: One public check at a time: the backend runs one replica, and a check is
#: CPU work in a thread.
_validation_lock = asyncio.Lock()

_values_cache = guide.ExistingValuesCache()

#: The ``database`` query parameter: the ids of ``guide.DATABASE_TYPES``.
AgentDatabase = Enum(  # type: ignore[misc]
    "AgentDatabase", {key: key for key in guide.DATABASE_TYPES}, type=str
)

MARKDOWN = "text/markdown; charset=utf-8"


def _urls() -> guide.Urls:
    return guide.Urls(site=public_base(), api=api_base())


async def _readmes(session: AsyncSession) -> Dict[str, str]:
    rows = await session.execute(select(DatabaseReadme))
    return {row.database: row.content for row in rows.scalars()}


async def _existing_values(database: str) -> Dict[str, str]:
    version = data_version()
    values = _values_cache.get(database, version)
    if values is None:
        values = await run_in_threadpool(guide.existing_values, database)
        _values_cache.put(database, version, settings.cache_max_age, values)
    return values


@router.get(
    "/guide",
    response_class=Response,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_agent_guide(session: AsyncSession = Depends(get_session)) -> Response:
    """The start page of the agent guide: the method and the databases."""
    readmes = await _readmes(session)
    return Response(guide.render_index(_urls(), readmes), media_type=MARKDOWN)


@router.get(
    "/guide/{database}",
    response_class=Response,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_agent_database_guide(
    database: str, session: AsyncSession = Depends(get_session)
) -> Response:
    """Everything an agent needs for one database, on one page."""
    if database not in guide.DATABASE_TYPES:
        known = ", ".join(guide.DATABASE_TYPES)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No database {database}. The databases are: {known}.",
        )
    readme = await session.get(DatabaseReadme, database)
    rows = await session.execute(
        select(DictionaryColumn)
        .where(DictionaryColumn.database == database)
        .order_by(DictionaryColumn.position)
    )
    columns = [
        DictionaryColumnModel(
            name=row.column_name,
            description=row.description,
            symbol=row.symbol,
            unit=row.unit,
            type=row.type,
            example=row.example,
            nullable=row.nullable,
            group=row.group,
        )
        for row in rows.scalars()
    ]
    page = guide.render_database(
        _urls(),
        database,
        readme.content if readme else None,
        columns,
        await _existing_values(database),
    )
    return Response(page, media_type=MARKDOWN)


def enforce_agent_request_size(request: Request) -> None:
    check_content_length(request, MAX_AGENT_BYTES)


@router.post("/validate", response_model=ValidationReport)
@limiter.limit("10/minute")
async def agent_validate(
    request: Request,
    file: UploadFile = File(...),
    database: AgentDatabase = Query(...),
    _: None = Depends(enforce_agent_request_size),
) -> ValidationReport:
    """Check a folder prepared for a submission, without an account.

    The same checks as the contribution form, ids already in the hub included.
    Data problems answer 200 with ``valid: false``; 4xx is for the transport.
    """
    if _validation_lock.locked():
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Another check is running. Retry in a few seconds.",
            headers={"Retry-After": "5"},
        )
    key = database.value
    async with _validation_lock:
        response = await validate_upload(
            file,
            guide.DATABASE_TYPES[key],
            check_duplicates=True,
            limit=MAX_AGENT_BYTES,
            repo_duplicates=False,
            in_thread=True,
        )
    report = ValidationReport(
        valid=response.valid,
        message=response.message,
        error_count=response.error_count,
        results=response.results,
    )
    if not report.results:
        # Nothing was found where the validator looks, so nothing failed:
        # without this, an archive with the wrong root would pass.
        report = _nothing_found(key)
    return report


def _nothing_found(database: str) -> ValidationReport:
    expected = guide.layout(database).primary_csv
    return ValidationReport(
        valid=False,
        message="Validation failed",
        error_count=1,
        results=[
            FileValidationResult(
                file=path.basename(expected),
                path=expected,
                valid=False,
                errors=[
                    ValidationIssue(
                        row=0,
                        column="file",
                        message=(
                            f"No file found at {expected}. The archive must "
                            f"have the {guide.layout(database).folder}/ folder "
                            "at its root."
                        ),
                    )
                ],
            )
        ],
    )
