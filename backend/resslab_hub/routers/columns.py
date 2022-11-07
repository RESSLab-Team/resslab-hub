"""
Handle /connections requests
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    ColumnField,
    ColumnModel,
    ColumnNumberField,
    CountModel,
    LocationModel,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.column import (
    ColumnAxialShortening,
    ColumnEntity,
    ColumnMomentStrong,
    ColumnMomentWeak,
)
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/columns",
    tags=["columns"],
)

component = Component(
    "columns",
    database_type=ColumnEntity,
    model_type=ColumnModel,
    id_column=ColumnEntity.id,
    ignored_columns={
        ColumnEntity.axial_shortening_count,
        ColumnEntity.moment_strong_count,
        ColumnEntity.moment_weak_count,
    },
)

axial_shortening_component = component.get_sub(
    "axial-shortening",
    ColumnAxialShortening.column_id,
    ColumnAxialShortening.id,
    {
        ColumnAxialShortening.chord_rotation: "Chord Rotation [rads]",
        ColumnAxialShortening.axial_shortening: "Axial Shortening [mm]",
    },
)
moment_strong_component = component.get_sub(
    "moment",
    ColumnMomentStrong.column_id,
    ColumnMomentStrong.id,
    {
        ColumnMomentStrong.chord_rotation: "Chord Rotation [rads]",
        ColumnMomentStrong.moment: "Moment [kN-mm]",
    },
)
moment_weak_component = component.get_sub(
    "moment",
    ColumnMomentWeak.column_id,
    ColumnMomentWeak.id,
    {
        ColumnMomentWeak.chord_rotation: "Chord Rotation [rads]",
        ColumnMomentWeak.moment: "Moment [kN-mm]",
    },
)


@router.get("", response_model=ExtendedPage[ColumnModel])
async def get_columns(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[ColumnModel]:
    """
    Get paginated Columns
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/locations", response_model=List[LocationModel])
async def get_columns_locations(
    session: AsyncSession = Depends(get_session),
):
    """
    Get occurences location of field values
    """

    rows = await session.execute(
        select(
            ColumnEntity.id,
            ColumnEntity.latitude,
            ColumnEntity.longitude,
            ColumnEntity.date,
            ColumnEntity.link,
            ColumnEntity.reference,
            # ColumnEntity.experimental_program,
            # ColumnEntity.boundary_condition,
            # ColumnEntity.section_c,
            # ColumnEntity.axial_lp,
            # ColumnEntity.specimen_designation,
        )
    )
    return rows.all()


@router.get("/counts", response_model=List[CountModel])
async def get_columns_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[ColumnField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_columns_range(
    session: AsyncSession = Depends(get_session),
    field: ColumnNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_columns_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[ColumnField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_columns_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/{column_id}/axial-shortening", response_model=List[List[Decimal]])
async def get_columns_axial_shortening(
    session: AsyncSession = Depends(get_session),
    column_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get axial shortening series from column
    """
    return await axial_shortening_component.get_series(session, column_id, size)


@router.get("/{column_id}/moment-strong", response_model=List[List[Decimal]])
async def get_columns_moment_strong(
    session: AsyncSession = Depends(get_session),
    column_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get moment strong series from column
    """
    return await moment_strong_component.get_series(session, column_id, size)


@router.get("/{column_id}/moment-weak", response_model=List[List[Decimal]])
async def get_columns_moment_weak(
    session: AsyncSession = Depends(get_session),
    column_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get moment weak series from column
    """
    return await moment_weak_component.get_series(session, column_id, size)
