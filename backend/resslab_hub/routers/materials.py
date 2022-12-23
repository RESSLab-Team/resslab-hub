"""
Handle /materials requests
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    CountModel,
    MaterialField,
    MaterialModel,
    MaterialNumberField,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.material import Material, MaterialStressStrain
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/materials",
    tags=["materials"],
)

component = Component(
    "materials",
    database_type=Material,
    model_type=MaterialModel,
    id_column=Material.id,
    ignored_columns={
        Material.stress_strain_count,
    },
)

stress_strain_component = component.get_sub(
    "stress-strain",
    MaterialStressStrain.material_id,
    MaterialStressStrain.id,
    {
        MaterialStressStrain.stress: "Stress",
        MaterialStressStrain.strain: "Strain",
    },
)


@router.get("", response_model=ExtendedPage[MaterialModel])
async def get_materials(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[MaterialModel]:
    """
    Get paginated Materials
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/counts", response_model=List[CountModel])
async def get_materials_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[MaterialField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_materials_range(
    session: AsyncSession = Depends(get_session),
    field: MaterialNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_materials_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[MaterialField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_materials_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/{material_id}/stress-strain", response_model=List[List[Decimal]])
async def get_materials_stress_strain(
    session: AsyncSession = Depends(get_session),
    material_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get Stress-Strain series from material
    """
    return await stress_strain_component.get_series(session, material_id, size)
