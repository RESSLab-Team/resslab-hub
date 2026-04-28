"""
Handle /tensile-coupon requests
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    CountModel,
    FieldsModel,
    MatrixModel,
    RangeModel,
    TensileCouponField,
    TensileCouponModel,
    TensileCouponNumberField,
)
from resslab_hub.models.database.tensile_coupon import (
    TensileCoupon,
    TensileCouponStressStrain,
)
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/tensile-coupon",
    tags=["tensile-coupon"],
)

component = Component(
    "tensile-coupon",
    database_type=TensileCoupon,
    model_type=TensileCouponModel,
    id_column=TensileCoupon.id,
    ignored_columns={
        TensileCoupon.stress_strain_count,
    },
)

stress_strain_component = component.get_sub(
    "stress-strain",
    TensileCouponStressStrain.tensile_coupon_id,
    TensileCouponStressStrain.id,
    {
        TensileCouponStressStrain.stress: "Stress",
        TensileCouponStressStrain.strain: "Strain",
    },
)


@router.get("", response_model=ExtendedPage[TensileCouponModel])
async def get_tensile_coupons(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[TensileCouponModel]:
    """
    Get paginated Tensile Coupons
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/fields", response_model=List[FieldsModel])
async def get_tensile_coupons_fields(
    session: AsyncSession = Depends(get_session),
    fields: List[TensileCouponField] = Query([]),
) -> List[FieldsModel]:
    """
    Get filtered fields
    """
    return await component.get_fields(session, [field.value for field in fields])


@router.get("/counts", response_model=List[CountModel])
async def get_tensile_coupons_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[TensileCouponField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_tensile_coupons_range(
    session: AsyncSession = Depends(get_session),
    field: TensileCouponNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_tensile_coupons_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[TensileCouponField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_tensile_coupons_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_tensile_coupons_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[TensileCouponField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields])


@router.get("/{tensile_coupon_id}/stress-strain", response_model=List[List[Decimal]])
async def get_tensile_coupons_stress_strain(
    session: AsyncSession = Depends(get_session),
    tensile_coupon_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get Stress-Strain series from tensile coupon
    """
    return await stress_strain_component.get_series(session, tensile_coupon_id, size)


@router.get("/{tensile_coupon_id}/stress-strain/csv", response_class=StreamingResponse)
async def get_tensile_coupons_stress_strain_csv(
    session: AsyncSession = Depends(get_session),
    tensile_coupon_id: str = Path(...),
) -> StreamingResponse:
    """
    Get Stress-Strain csv
    """
    return await stress_strain_component.get_csv(session, tensile_coupon_id)
