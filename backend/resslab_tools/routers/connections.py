"""
Handle /connections requests
"""
import math
from decimal import Decimal
from distutils.util import strtobool
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.async_sqlalchemy import paginate
from resslab_tools.models.api import (ConnectionColumn, ConnectionModel,
                                      CountModel)
from resslab_tools.models.database import (Connection, ConnectionGlobal,
                                           ConnectionPanelZone)
from resslab_tools.services.database import get_session
from sqlalchemy import and_, desc, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.sqltypes import Boolean, Integer, String

router = APIRouter(
    prefix='/connections',
    tags=['connections'],
)


@router.get('', response_model=Page[ConnectionModel])
async def get_connections(
        session: AsyncSession = Depends(get_session),
        query: Optional[str] = Query(None),
        sort_by: List[str] = Query([]),
        sort_desc: List[bool] = Query([]),
):
    """
    Get paginated Connections
    """
    where_clauses: List[Any] = __get_where_clauses(query)
    order_clauses: List[Any] = [Connection.__dict__[key]
                                if not is_desc
                                else desc(Connection.__dict__[key])
                                for key, is_desc
                                in zip(sort_by, sort_desc)]
    return await paginate(
        session,
        select(Connection)
        .where(and_(*where_clauses))
        .order_by(*order_clauses)
    )


@router.get('/counts', response_model=List[CountModel])
async def get_counts(
    session: AsyncSession = Depends(get_session),
    fields: List[ConnectionColumn] = Query(...),
    query: Optional[str] = Query(None),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    where_clauses: List[Any] = __get_where_clauses(query)
    columns = [Connection.__dict__[field.value] for field in fields]
    tuples = await session.execute(
        select([*columns, func.count()])
        .where(and_(*where_clauses))
        .group_by(func.grouping_sets(tuple_(*columns)))
    )
    return [CountModel(names=list(tuple)[:-1], value=tuple[len(columns)])
            for tuple in tuples]


@router.get('/{connection_id}/globals', response_model=List[List[Decimal]])
async def get_globals(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get global series from connection
    """
    return await __get_series(
        session,
        size,
        select([
            ConnectionGlobal.story_drift_angle,
            ConnectionGlobal.actuator_force,
        ])
        .where(ConnectionGlobal.connection_id == connection_id),
        ConnectionGlobal.id
    )


@router.get('/{connection_id}/panel-zones', response_model=List[List[Decimal]])
async def get_panel_zones(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
    size: int = Query(1024, ge=0),
) -> List[List[Decimal]]:
    """
    Get panel zone series from connection
    """
    return await __get_series(
        session,
        size,
        select([
            ConnectionPanelZone.shear_distortion,
            ConnectionPanelZone.shear_force,
        ])
        .where(ConnectionPanelZone.connection_id == connection_id),
        ConnectionPanelZone.id
    )


async def __get_series(
        session: AsyncSession,
        size: int,
        statement: Select,
        id_column: Column[int]
) -> List[List[Decimal]]:
    if size > 0:
        count: int = await session.scalar(
            select(func.count()).select_from(statement))
        if count == 0:
            return []
        if count <= size:
            tuples = await session.execute(statement)
        else:
            n = math.ceil(float(count) / float(size))
            tuples = await session.execute(
                statement.where(func.mod(id_column, n) == 0))
    else:
        tuples = await session.execute(statement)
    return [[tuple[0], tuple[1]] for tuple in tuples]


def __get_where_clause(query: str) -> Any:
    """
    Get where clause
    """
    if ':' not in query:
        return or_(*[column.cast(String).ilike(query)
                     for column
                     in Connection.__table__.columns])
    key, expression = query.split(':', 2)
    column: Column[Any] = Connection.__dict__[key]
    if expression.startswith('<'):
        return column < int(expression[1:])
    if expression.startswith('>'):
        return column > int(expression[1:])
    if isinstance(column.type, String):
        return column.ilike(expression)
    if isinstance(column.type, Integer):
        return column == int(expression)
    if isinstance(column.type, Boolean):
        return column == bool(strtobool(expression))
    if ',' in expression:
        return column.in_(expression.split(','))
    return column == expression


def __get_where_clauses(query: Optional[str]) -> List[Any]:
    """
    Get where clauses
    """
    return [__get_where_clause(q)
            for q
            in query.split(';')
            ] if query else []
