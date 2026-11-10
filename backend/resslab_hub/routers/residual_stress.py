"""
Handle /residual-stress requests
"""

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
    ResidualStressField,
    ResidualStressModel,
    ResidualStressNumberField,
)
from resslab_hub.models.database.residual_stress import (
    ResidualStress,
    ResidualStressDistributionF1,
    ResidualStressDistributionF2,
    ResidualStressDistributionW1,
    ResidualStressQPCoefficient,
)
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/residual-stress",
    tags=["residual-stress"],
)

component = Component(
    "residual-stress",
    database_type=ResidualStress,
    model_type=ResidualStressModel,
    id_column=ResidualStress.id,
    ignored_columns={
        ResidualStress.not_reported,
        ResidualStress.qp_coefficient_count,
        ResidualStress.distribution_F1_count,
        ResidualStress.distribution_F2_count,
        ResidualStress.distribution_W1_count,
    },  # type: ignore
)

qp_coefficient_component = component.get_sub(
    "qp_coefficient",
    ResidualStressQPCoefficient.residual_stress_id,
    ResidualStressQPCoefficient.id,
    {
        ResidualStressQPCoefficient.qp_coefficient: "QP Coefficient",
    },
)

distribution_f1_component = component.get_sub(
    "distribution_f1",
    ResidualStressDistributionF1.residual_stress_id,
    ResidualStressDistributionF1.id,
    {
        ResidualStressDistributionF1.coordinate: "Coordinate",
        ResidualStressDistributionF1.residual_stress: "Residual Stress",
    },
)

distribution_f2_component = component.get_sub(
    "distribution_f2",
    ResidualStressDistributionF2.residual_stress_id,
    ResidualStressDistributionF2.id,
    {
        ResidualStressDistributionF2.coordinate: "Coordinate",
        ResidualStressDistributionF2.residual_stress: "Residual Stress",
    },
)

distribution_w1_component = component.get_sub(
    "distribution_w1",
    ResidualStressDistributionW1.residual_stress_id,
    ResidualStressDistributionW1.id,
    {
        ResidualStressDistributionW1.coordinate: "Coordinate",
        ResidualStressDistributionW1.residual_stress: "Residual Stress",
    },
)


@router.get("", response_model=ExtendedPage[ResidualStressModel])
async def get_residual_stresses(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[ResidualStressModel]:
    """
    Get paginated Residual Stresses
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/fields", response_model=List[FieldsModel])
async def get_residual_stresses_fields(
    session: AsyncSession = Depends(get_session),
    fields: List[ResidualStressField] = Query([]),
) -> List[FieldsModel]:
    """
    Get filtered fields
    """
    return await component.get_fields(session, [field.value for field in fields])


@router.get("/counts", response_model=List[CountModel])
async def get_residual_stresses_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[ResidualStressField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_residual_stresses_range(
    session: AsyncSession = Depends(get_session),
    field: ResidualStressNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_residual_stresses_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[ResidualStressField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_residual_stresses_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_residual_stresses_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[ResidualStressField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields]) or 0


@router.get("/{ResidualStress_id}/distribution-f1", response_model=List[List[float]])
async def get_residual_stresses_distribution_f1(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get distribution-f1 series from ResidualStress
    """
    return await distribution_f1_component.get_series(session, ResidualStress_id, size)


@router.get(
    "/{ResidualStress_id}/distribution-f1/csv", response_class=StreamingResponse
)
async def get_residual_stresses_distribution_f1_csv(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
) -> StreamingResponse:
    """
    Get distribution-f1 csv
    """
    return await distribution_f1_component.get_csv(session, ResidualStress_id)


@router.get("/{ResidualStress_id}/distribution-f2", response_model=List[List[float]])
async def get_residual_stresses_distribution_f2(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get distribution-f2 series from ResidualStress
    """
    return await distribution_f2_component.get_series(session, ResidualStress_id, size)


@router.get(
    "/{ResidualStress_id}/distribution-f2/csv", response_class=StreamingResponse
)
async def get_residual_stresses_distribution_f2_csv(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
) -> StreamingResponse:
    """
    Get distribution-f2 csv
    """
    return await distribution_f2_component.get_csv(session, ResidualStress_id)


@router.get("/{ResidualStress_id}/distribution-w1", response_model=List[List[float]])
async def get_residual_stresses_distribution_w1(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get distribution-w1 series from ResidualStress
    """
    return await distribution_w1_component.get_series(session, ResidualStress_id, size)


@router.get(
    "/{ResidualStress_id}/distribution-w1/csv", response_class=StreamingResponse
)
async def get_residual_stresses_distribution_w1_csv(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
) -> StreamingResponse:
    """
    Get distribution-w1 csv
    """
    return await distribution_w1_component.get_csv(session, ResidualStress_id)


@router.get("/{ResidualStress_id}/qp-coefficient", response_model=List[List[float]])
async def get_residual_stresses_qp_coefficient(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get qp-coefficient series from ResidualStress
    """
    return await qp_coefficient_component.get_series(session, ResidualStress_id, size)


@router.get("/{ResidualStress_id}/qp-coefficient/csv", response_class=StreamingResponse)
async def get_residual_stresses_qp_coefficient_csv(
    session: AsyncSession = Depends(get_session),
    ResidualStress_id: str = Path(...),
) -> StreamingResponse:
    """
    Get qp-coefficient csv
    """
    return await qp_coefficient_component.get_csv(session, ResidualStress_id)
