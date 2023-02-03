"""
Handle /braces requests
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    BraceField,
    BraceModel,
    BraceNumberField,
    CountModel,
    LocationBracesModel,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.brace import Brace, BraceDisplacement
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/braces",
    tags=["braces"],
)

component = Component(
    "braces",
    database_type=Brace,
    model_type=BraceModel,
    id_column=Brace.id,
    ignored_columns={
        Brace.displacement_count,
    },
)

displacement_component = component.get_sub(
    "displacement",
    BraceDisplacement.brace_id,
    BraceDisplacement.id,
    {
        BraceDisplacement.displacement: "Displacement [mm]",
        BraceDisplacement.force: "Force [kN]",
    },
)


@router.get("", response_model=ExtendedPage[BraceModel])
async def get_braces(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[BraceModel]:
    """
    Get paginated Braces
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/locations", response_model=List[LocationBracesModel])
async def get_braces_locations(
    session: AsyncSession = Depends(get_session),
):
    """
    Get occurences location of field values
    """

    rows = await session.execute(
        select(
            Brace.id,
            Brace.investigator,
            Brace.latitude,
            Brace.longitude,
            Brace.date,
            Brace.reference,
            Brace.link,
            Brace.cross_section_size,
            Brace.kl_r,
            Brace.boundary_condition,
        )
    )
    return rows.all()


@router.get("/counts", response_model=List[CountModel])
async def get_braces_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[BraceField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_braces_range(
    session: AsyncSession = Depends(get_session),
    field: BraceNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_braces_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[BraceField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_braces_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_braces_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[BraceField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields])


@router.get("/{brace_id}/displacement", response_model=List[List[Decimal]])
async def get_braces_displacement(
    session: AsyncSession = Depends(get_session),
    brace_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get displacement series from brace
    """
    return await displacement_component.get_series(session, brace_id, size)


@router.get("/{brace_id}/displacement/csv", response_class=StreamingResponse)
async def get_braces_displacement_csv(
    session: AsyncSession = Depends(get_session),
    brace_id: str = Path(...),
) -> StreamingResponse:
    """
    Get displacement csv
    """
    return await displacement_component.get_csv(session, brace_id)
