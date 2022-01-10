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
    ConnectionGlobal,
    ConnectionGlobalWest,
    ConnectionPanelZone,
)
from resslab_tools.utils.common import Api
from resslab_tools.utils.database import get_session
from resslab_tools.utils.pagination import ExtendedPage

router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)

api = Api(
    "connections",
    database_type=Connection,
    model_type=ConnectionModel,
    id_column=Connection.id,
    ignored_columns={
        Connection.global_count,
        Connection.global_west_count,
        Connection.panel_zone_count,
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
    return await api.get_page(session, query, sort_by, sort_desc)


@router.get("/counts", response_model=List[CountModel])
async def get_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[ConnectionField] = Query([]),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    return await api.get_counts(session, [field.value for field in fields], query)


@router.get("/range", response_model=RangeModel)
async def get_range(
    session: AsyncSession = Depends(get_session),
    field: ConnectionNumberField = Query(...),
) -> RangeModel:
    """
    Get range of field
    """
    return await api.get_range(session, field.value)


@router.get("/matrix", response_model=MatrixModel)
async def get_matrix(
    session: AsyncSession = Depends(get_session),
    fields: List[ConnectionField] = Query(...),
    query: Optional[str] = Query(None),
) -> MatrixModel:
    return await api.get_matrix(session, [field.value for field in fields], query)


@router.get("/csv", response_class=StreamingResponse)
async def get_csv(
    session: AsyncSession = Depends(get_session),
    ids: List[str] = Query([]),
) -> StreamingResponse:
    """
    Get master csv
    """
    return await api.get_csv(session, ids)


@router.get("/{connection_id}/globals", response_model=List[List[Decimal]])
async def get_globals(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get global series from connection
    """
    return await api.get_series(
        session,
        select(
            [
                ConnectionGlobal.story_drift_angle,
                ConnectionGlobal.actuator_force,
            ]
        )
        .where(ConnectionGlobal.connection_id == connection_id)
        .order_by(ConnectionGlobal.id),
        ConnectionGlobal.id,
        size,
    )


@router.get("/{connection_id}/globals/csv", response_class=StreamingResponse)
async def get_global_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get global csv from connection
    """
    filename = f"connection-global_{connection_id}.csv"
    return api.get_csv_response(
        session,
        select(
            [
                ConnectionGlobal.story_drift_angle,
                ConnectionGlobal.actuator_force,
            ]
        )
        .where(ConnectionGlobal.connection_id == connection_id)
        .order_by(ConnectionGlobal.id),
        ["Total story drift angle [rad]", "Force in the actuator [kN]"],
        filename,
    )


@router.get("/{connection_id}/global-west", response_model=List[List[Decimal]])
async def get_global_west(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get global west series from connection
    """
    return await api.get_series(
        session,
        select(
            [
                ConnectionGlobalWest.story_drift_angle,
                ConnectionGlobalWest.actuator_force,
            ]
        )
        .where(ConnectionGlobalWest.connection_id == connection_id)
        .order_by(ConnectionGlobalWest.id),
        ConnectionGlobalWest.id,
        size,
    )


@router.get("/{connection_id}/global-west/csv", response_class=StreamingResponse)
async def get_global_west_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get global west csv from connection
    """
    filename = f"connection-global-west_{connection_id}.csv"
    return api.get_csv_response(
        session,
        select(
            [
                ConnectionGlobalWest.story_drift_angle,
                ConnectionGlobalWest.actuator_force,
            ]
        )
        .where(ConnectionGlobalWest.connection_id == connection_id)
        .order_by(ConnectionGlobalWest.id),
        ["Total story drift angle [rad]", "Force in the actuator [kN]"],
        filename,
    )


@router.get("/{connection_id}/panel-zones", response_model=List[List[Decimal]])
async def get_panel_zones(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get panel zone series from connection
    """
    return await api.get_series(
        session,
        select(
            [
                ConnectionPanelZone.shear_distortion,
                ConnectionPanelZone.shear_force,
            ]
        )
        .where(ConnectionPanelZone.connection_id == connection_id)
        .order_by(ConnectionPanelZone.id),
        ConnectionPanelZone.id,
        size,
    )


@router.get("/{connection_id}/panel-zones/csv", response_class=StreamingResponse)
async def get_panel_zones_csv(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> StreamingResponse:
    """
    Get panel zone csv from connection
    """
    filename = f"connection-panel-zone_{connection_id}.csv"
    return api.get_csv_response(
        session,
        select(
            [
                ConnectionPanelZone.shear_distortion,
                ConnectionPanelZone.shear_force,
            ]
        )
        .where(ConnectionPanelZone.connection_id == connection_id)
        .order_by(ConnectionPanelZone.id),
        ["Panel zone shear distortion [rad]", "Panel zone shear force [kN]"],
        filename,
    )
