"""
Handle /hss-column requests
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    CountModel,
    FieldsModel,
    HSSColumnField,
    HSSColumnModel,
    HSSColumnNumberField,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.hss_column import HSSColumn, HSSColumnMomentRotation
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/hss-column",
    tags=["hss-column"],
)

component = Component(
    "hss-column",
    database_type=HSSColumn,
    model_type=HSSColumnModel,
    id_column=HSSColumn.id,
    ignored_columns={
        HSSColumn.not_reported,
        HSSColumn.moment_rotation_count,
    },  # type: ignore
)

moment_rotation_component = component.get_sub(
    "moment_rotation",
    HSSColumnMomentRotation.hss_column_id,
    HSSColumnMomentRotation.id,
    {
        HSSColumnMomentRotation.rotation: "Rotation",
        HSSColumnMomentRotation.moment: "Moment",
    },
)


@router.get("", response_model=ExtendedPage[HSSColumnModel])
async def get_hss_columns(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[HSSColumnModel]:
    """
    Get paginated HSS Columns
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/fields", response_model=List[FieldsModel])
async def get_hss_columns_fields(
    session: AsyncSession = Depends(get_session),
    fields: List[HSSColumnField] = Query([]),
) -> List[FieldsModel]:
    """
    Get filtered fields
    """
    return await component.get_fields(session, [field.value for field in fields])


@router.get("/counts", response_model=List[CountModel])
async def get_hss_columns_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[HSSColumnField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_hss_columns_range(
    session: AsyncSession = Depends(get_session),
    field: HSSColumnNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_hss_columns_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[HSSColumnField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_hss_columns_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_hss_columns_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[HSSColumnField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields])


@router.get("/{HSSColumn_id}/moment-rotation", response_model=List[List[float]])
async def get_hss_columns_moment_rotation(
    session: AsyncSession = Depends(get_session),
    HSSColumn_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get moment-rotation series from HSSColumn
    """
    return await moment_rotation_component.get_series(session, HSSColumn_id, size)


@router.get("/{HSSColumn_id}/moment-rotation/csv", response_class=StreamingResponse)
async def get_hss_columns_moment_rotation_csv(
    session: AsyncSession = Depends(get_session),
    HSSColumn_id: str = Path(...),
) -> StreamingResponse:
    """
    Get moment-rotation csv
    """
    return await moment_rotation_component.get_csv(session, HSSColumn_id)
