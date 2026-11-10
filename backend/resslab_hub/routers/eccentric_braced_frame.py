"""
Handle /eccentric-braced-frame requests
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    CountModel,
    EccentricBracedFrameField,
    EccentricBracedFrameModel,
    EccentricBracedFrameNumberField,
    FieldsModel,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.eccentric_braced_frame import (
    EccentricBracedFrame,
    EccentricBracedFrameShearLinkAngle,
)
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/eccentric-braced-frame",
    tags=["eccentric-braced-frame"],
)

component = Component(
    "eccentric-braced-frame",
    database_type=EccentricBracedFrame,
    model_type=EccentricBracedFrameModel,
    id_column=EccentricBracedFrame.id,
    ignored_columns={
        EccentricBracedFrame.not_reported,
        EccentricBracedFrame.shear_link_angle_count,
    },  # type: ignore
)

shear_link_angle_component = component.get_sub(
    "shear-link-angle",
    EccentricBracedFrameShearLinkAngle.eccentric_braced_frame_id,
    EccentricBracedFrameShearLinkAngle.id,
    {
        EccentricBracedFrameShearLinkAngle.gamma_t: "Shear Link Angle",
        EccentricBracedFrameShearLinkAngle.v: "Shear Force",
    },
)


@router.get("", response_model=ExtendedPage[EccentricBracedFrameModel])
async def get_eccentric_braced_frames(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[EccentricBracedFrameModel]:
    """
    Get paginated Eccentric Braced Frames
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/fields", response_model=List[FieldsModel])
async def get_eccentric_braced_frames_fields(
    session: AsyncSession = Depends(get_session),
    fields: List[EccentricBracedFrameField] = Query([]),
) -> List[FieldsModel]:
    """
    Get filtered fields
    """
    return await component.get_fields(session, [field.value for field in fields])


@router.get("/counts", response_model=List[CountModel])
async def get_eccentric_braced_frames_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[EccentricBracedFrameField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurrences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_eccentric_braced_frames_range(
    session: AsyncSession = Depends(get_session),
    field: EccentricBracedFrameNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_eccentric_braced_frames_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[EccentricBracedFrameField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_eccentric_braced_frames_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_eccentric_braced_frames_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[EccentricBracedFrameField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields]) or 0


@router.get(
    "/{eccentric_braced_frame_id}/shear-link-angle", response_model=List[List[float]]
)
async def get_eccentric_braced_frames_shear_link_angle(
    session: AsyncSession = Depends(get_session),
    eccentric_braced_frame_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get shear-link-angle series from Eccentric Braced Frame
    """
    return await shear_link_angle_component.get_series(
        session, eccentric_braced_frame_id, size
    )


@router.get(
    "/{eccentric_braced_frame_id}/shear-link-angle/csv",
    response_class=StreamingResponse,
)
async def get_eccentric_braced_frames_shear_link_angle_csv(
    session: AsyncSession = Depends(get_session),
    eccentric_braced_frame_id: str = Path(...),
) -> StreamingResponse:
    """
    Get shear-link-angle csv
    """
    return await shear_link_angle_component.get_csv(session, eccentric_braced_frame_id)
