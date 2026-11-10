"""
Handle /ductile-fracture requests
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import (
    CountModel,
    DuctileFractureField,
    DuctileFractureModel,
    DuctileFractureNumberField,
    FieldsModel,
    MatrixModel,
    RangeModel,
)
from resslab_hub.models.database.ductile_fracture import (
    DuctileFracture,
    DuctileFractureEpeqSimulation,
    DuctileFractureForceElongation,
    DuctileFractureForceElongationSimulation,
    DuctileFractureForceRadial,
    DuctileFractureForceRadialSimulation,
    DuctileFractureLodeSimulation,
    DuctileFractureTriaxSimulation,
)
from resslab_hub.utils.common import Component
from resslab_hub.utils.database import get_session
from resslab_hub.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/ductile-fracture",
    tags=["ductile-fracture"],
)

component = Component(
    "ductile-fracture",
    database_type=DuctileFracture,
    model_type=DuctileFractureModel,
    id_column=DuctileFracture.id,
    ignored_columns={
        DuctileFracture.not_reported,
        DuctileFracture.force_elongation_count,
        DuctileFracture.force_elongation_simulation_count,
        DuctileFracture.force_radial_count,
        DuctileFracture.force_radial_simulation_count,
        DuctileFracture.epeq_simulation_count,
        DuctileFracture.lode_simulation_count,
        DuctileFracture.triax_simulation_count,
    },
)

force_elongation_component = component.get_sub(
    "force-elongation",
    DuctileFractureForceElongation.ductile_fracture_id,
    DuctileFractureForceElongation.id,
    {
        DuctileFractureForceElongation.elongation: "Elongation",
        DuctileFractureForceElongation.load: "Load",
    },
)

force_elongation_simulation_component = component.get_sub(
    "force-elongation-simulation",
    DuctileFractureForceElongationSimulation.ductile_fracture_id,
    DuctileFractureForceElongationSimulation.id,
    {
        DuctileFractureForceElongationSimulation.elongation: "Elongation",
        DuctileFractureForceElongationSimulation.load: "Load",
    },
)

force_radial_component = component.get_sub(
    "force-radial",
    DuctileFractureForceRadial.ductile_fracture_id,
    DuctileFractureForceRadial.id,
    {
        DuctileFractureForceRadial.elongation: "Elongation",
        DuctileFractureForceRadial.load: "Load",
    },
)

force_radial_simulation_component = component.get_sub(
    "force-radial-simulation",
    DuctileFractureForceRadialSimulation.ductile_fracture_id,
    DuctileFractureForceRadialSimulation.id,
    {
        DuctileFractureForceRadialSimulation.elongation: "Elongation",
        DuctileFractureForceRadialSimulation.load: "Load",
    },
)

epeq_simulation_component = component.get_sub(
    "epeq-simulation",
    DuctileFractureEpeqSimulation.ductile_fracture_id,
    DuctileFractureEpeqSimulation.id,
    {
        DuctileFractureEpeqSimulation.elongation: "Elongation",
        DuctileFractureEpeqSimulation.peeq: "PEEQ",
    },
)

lode_simulation_component = component.get_sub(
    "lode-simulation",
    DuctileFractureLodeSimulation.ductile_fracture_id,
    DuctileFractureLodeSimulation.id,
    {
        DuctileFractureLodeSimulation.elongation: "Elongation",
        DuctileFractureLodeSimulation.lode: "Lode",
    },
)

triax_simulation_component = component.get_sub(
    "triax-simulation",
    DuctileFractureTriaxSimulation.ductile_fracture_id,
    DuctileFractureTriaxSimulation.id,
    {
        DuctileFractureTriaxSimulation.elongation: "Elongation",
        DuctileFractureTriaxSimulation.triaxiality: "Triaxiality",
    },
)


@router.get("", response_model=ExtendedPage[DuctileFractureModel])
async def get_ductile_fractures(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[DuctileFractureModel]:
    """
    Get paginated Ductile Fractures
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/fields", response_model=List[FieldsModel])
async def get_ductile_fractures_fields(
    session: AsyncSession = Depends(get_session),
    fields: List[DuctileFractureField] = Query([]),
) -> List[FieldsModel]:
    """
    Get filtered fields
    """
    return await component.get_fields(session, [field.value for field in fields])


@router.get("/counts", response_model=List[CountModel])
async def get_ductile_fractures_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[DuctileFractureField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_ductile_fractures_range(
    session: AsyncSession = Depends(get_session),
    field: DuctileFractureNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_ductile_fractures_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[DuctileFractureField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_ductile_fractures_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/distinct", response_model=int)
async def get_ductile_fractures_distinct(
    session: AsyncSession = Depends(get_session),
    fields: List[DuctileFractureField] = Query([]),
) -> int:
    """
    Get distinct count
    """
    return await component.get_distinct(session, [field.value for field in fields])


@router.get("/{ductile_fracture_id}/force-elongation", response_model=List[List[float]])
async def get_ductile_fractures_force_elongation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Force-Elongation test series
    """
    return await force_elongation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/force-elongation/csv", response_class=StreamingResponse
)
async def get_ductile_fractures_force_elongation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await force_elongation_component.get_csv(session, ductile_fracture_id)


@router.get(
    "/{ductile_fracture_id}/force-elongation-simulation",
    response_model=List[List[float]],
)
async def get_ductile_fractures_force_elongation_simulation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Force-Elongation simulation series
    """
    return await force_elongation_simulation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/force-elongation-simulation/csv",
    response_class=StreamingResponse,
)
async def get_ductile_fractures_force_elongation_simulation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await force_elongation_simulation_component.get_csv(
        session, ductile_fracture_id
    )


@router.get("/{ductile_fracture_id}/force-radial", response_model=List[List[float]])
async def get_ductile_fractures_force_radial(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Force-Radial elongation test series
    """
    return await force_radial_component.get_series(session, ductile_fracture_id, size)


@router.get("/{ductile_fracture_id}/force-radial/csv", response_class=StreamingResponse)
async def get_ductile_fractures_force_radial_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await force_radial_component.get_csv(session, ductile_fracture_id)


@router.get(
    "/{ductile_fracture_id}/force-radial-simulation",
    response_model=List[List[float]],
)
async def get_ductile_fractures_force_radial_simulation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Force-Radial elongation simulation series
    """
    return await force_radial_simulation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/force-radial-simulation/csv",
    response_class=StreamingResponse,
)
async def get_ductile_fractures_force_radial_simulation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await force_radial_simulation_component.get_csv(session, ductile_fracture_id)


@router.get("/{ductile_fracture_id}/epeq-simulation", response_model=List[List[float]])
async def get_ductile_fractures_epeq_simulation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Equivalent Plastic Strain - Elongation simulation series
    """
    return await epeq_simulation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/epeq-simulation/csv", response_class=StreamingResponse
)
async def get_ductile_fractures_epeq_simulation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await epeq_simulation_component.get_csv(session, ductile_fracture_id)


@router.get("/{ductile_fracture_id}/lode-simulation", response_model=List[List[float]])
async def get_ductile_fractures_lode_simulation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Lode angle - Elongation simulation series
    """
    return await lode_simulation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/lode-simulation/csv", response_class=StreamingResponse
)
async def get_ductile_fractures_lode_simulation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await lode_simulation_component.get_csv(session, ductile_fracture_id)


@router.get("/{ductile_fracture_id}/triax-simulation", response_model=List[List[float]])
async def get_ductile_fractures_triax_simulation(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[float]]:
    """
    Get Triaxiality - Elongation simulation series
    """
    return await triax_simulation_component.get_series(
        session, ductile_fracture_id, size
    )


@router.get(
    "/{ductile_fracture_id}/triax-simulation/csv", response_class=StreamingResponse
)
async def get_ductile_fractures_triax_simulation_csv(
    session: AsyncSession = Depends(get_session),
    ductile_fracture_id: str = Path(...),
) -> StreamingResponse:
    return await triax_simulation_component.get_csv(session, ductile_fracture_id)
