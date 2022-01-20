"""
Handle /connections requests
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_tools.models.api import (
    ConnectionField,
    ConnectionModel,
    ConnectionNumberField,
    CountModel,
    MatrixModel,
    RangeModel,
)
from resslab_tools.models.database import (
    Connection,
    ConnectionBeam,
    ConnectionBeamWest,
    ConnectionGlobal,
    ConnectionGlobalWest,
    ConnectionPanelZone,
)
from resslab_tools.utils.common import Component
from resslab_tools.utils.database import get_session
from resslab_tools.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)

component = Component(
    "connections",
    database_type=Connection,
    model_type=ConnectionModel,
    id_column=Connection.id,
    ignored_columns={
        Connection.beam_count,
        Connection.beam_west_count,
        Connection.global_count,
        Connection.global_west_count,
        Connection.panel_zone_count,
    },
)

beam_component = component.get_sub(
    "beam",
    ConnectionBeam.connection_id,
    ConnectionBeam.id,
    {
        ConnectionBeam.chord_rotation: "Chord Rotation [rads]",
        ConnectionBeam.moment: "Moment [kN-mm]",
    },
)
beam_west_component = component.get_sub(
    "beam-west",
    ConnectionBeamWest.connection_id,
    ConnectionBeamWest.id,
    {
        ConnectionBeamWest.chord_rotation: "Chord Rotation [rads]",
        ConnectionBeamWest.moment: "Moment [kN-mm]",
    },
)
global_component = component.get_sub(
    "global",
    ConnectionGlobal.connection_id,
    ConnectionGlobal.id,
    {
        ConnectionGlobal.story_drift_angle: "Total story drift angle [rad]",
        ConnectionGlobal.actuator_force: "Force in the actuator [kN]",
    },
)
global_west_component = component.get_sub(
    "global-west",
    ConnectionGlobalWest.connection_id,
    ConnectionGlobalWest.id,
    {
        ConnectionGlobalWest.story_drift_angle: "Total story drift angle [rad]",
        ConnectionGlobalWest.actuator_force: "Force in the actuator [kN]",
    },
)
panel_zone_component = component.get_sub(
    "panel-zone",
    ConnectionPanelZone.connection_id,
    ConnectionPanelZone.id,
    {
        ConnectionPanelZone.shear_distortion: "Panel zone shear distortion [rad]",
        ConnectionPanelZone.shear_force: "Panel zone shear force [kN]",
    },
)


@router.get("", response_model=ExtendedPage[ConnectionModel])
async def get_connections(
    session: AsyncSession = Depends(get_session),
    query: Optional[str] = Query(None),
    sort_by: List[str] = Query([]),
    sort_desc: List[bool] = Query([]),
) -> Page[ConnectionModel]:
    """
    Get paginated Connections
    """
    return await component.get_page(session, query, sort_by, sort_desc)


@router.get("/counts", response_model=List[CountModel])
async def get_connections_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[ConnectionField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await component.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_connections_range(
    session: AsyncSession = Depends(get_session),
    field: ConnectionNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await component.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_connections_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[ConnectionField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await component.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_connections_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await component.get_csv(session, ids)


@router.get("/{connection_id}/beam", response_model=List[List[Decimal]])
async def get_connections_beam(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get beam series from connection
    """
    return await beam_component.get_series(session, connection_id, size)


@router.get("/{connection_id}/beam/csv", response_class=StreamingResponse)
async def get_connections_beam_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get beam csv from connection
    """
    return await beam_component.get_csv(session, connection_id)


@router.get("/{connection_id}/beam-west", response_model=List[List[Decimal]])
async def get_connections_beam_west(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get beam west series from connection
    """
    return await beam_west_component.get_series(session, connection_id, size)


@router.get("/{connection_id}/beam-west/csv", response_class=StreamingResponse)
async def get_connections_beam_west_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get beam west csv from connection
    """
    return await beam_west_component.get_csv(session, connection_id)


@router.get("/{connection_id}/global", response_model=List[List[Decimal]])
async def get_connections_global(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get global series from connection
    """
    return await global_component.get_series(session, connection_id, size)


@router.get("/{connection_id}/global/csv", response_class=StreamingResponse)
async def get_connections_global_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get global csv from connection
    """
    return await global_component.get_csv(session, connection_id)


@router.get("/{connection_id}/global-west", response_model=List[List[Decimal]])
async def get_connections_global_west(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get global west series from connection
    """
    return await global_west_component.get_series(session, connection_id, size)


@router.get("/{connection_id}/global-west/csv", response_class=StreamingResponse)
async def get_connections_global_west_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get global west csv from connection
    """
    return await global_west_component.get_csv(session, connection_id)


@router.get("/{connection_id}/panel-zones", response_model=List[List[Decimal]])
async def get_connections_panel_zones(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get panel zone series from connection
    """
    return await panel_zone_component.get_series(session, connection_id, size)


@router.get("/{connection_id}/panel-zones/csv", response_class=StreamingResponse)
async def get_connections_panel_zones_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get panel zone csv from connection
    """
    return await panel_zone_component.get_csv(session, connection_id)
