"""
Handle /connections requests
"""
from decimal import Decimal
from distutils.util import strtobool
from functools import reduce
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.async_sqlalchemy import paginate
from resslab_tools.models.api import (ConnectionColumn, ConnectionModel,
                                      CountModel)
from resslab_tools.models.database import (Connection, ConnectionGlobal,
                                           ConnectionPanelZone)
from resslab_tools.services.database import get_session
from sqlalchemy import desc, func, or_, select
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
    where_clauses: List[Any] = [__query_to_where_clause(q)
                                for q
                                in query.split(';')] \
        if query \
        else []
    order_clauses: List[Any] = [Connection.__dict__[key]
                                if not is_desc
                                else desc(Connection.__dict__[key])
                                for key, is_desc
                                in zip(sort_by, sort_desc)]
    select_query: Select = reduce(lambda acc, item: acc.where(item),
                                  where_clauses,
                                  select(Connection))
    return await paginate(session, select_query.order_by(*order_clauses))


@router.get('/counts', response_model=List[CountModel])
async def get_counts(
    session: AsyncSession = Depends(get_session),
    field: ConnectionColumn = Query(...),
) -> List[CountModel]:
    """
    Get occurences count of field values
    """
    column = Connection.__dict__[field.value]
    tuples = await session.execute(select([column, func.count()])
                                   .group_by(column))
    return [CountModel(name=tuple[0], value=tuple[1]) for tuple in tuples]


@router.get('/{connection_id}/globals', response_model=List[List[Decimal]])
async def get_globals(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> List[List[Decimal]]:
    """
    Get global series from connection
    """
    tuples = await session.execute(
        select([
            ConnectionGlobal.story_drift_angle,
            ConnectionGlobal.actuator_force,
        ])
        .where(ConnectionGlobal.connection_id == connection_id))
    return [[tuple[0], tuple[1]] for tuple in tuples]


@router.get('/{connection_id}/panel-zones', response_model=List[List[Decimal]])
async def get_panel_zones(
    session: AsyncSession = Depends(get_session),
    connection_id: str = Path(...),
) -> List[List[Decimal]]:
    """
    Get panel zone series from connection
    """
    tuples = await session.execute(
        select([
            ConnectionPanelZone.shear_distortion,
            ConnectionPanelZone.shear_force,
        ])
        .where(ConnectionPanelZone.connection_id == connection_id))
    return [[tuple[0], tuple[1]] for tuple in tuples]


def __query_to_where_clause(query: str):
    """
    Get where clause
    """
    if ':' not in query:
        return or_(*[column.cast(String).ilike(query)
                     for column
                     in Connection.__table__.columns])
    key, expression = query.split(':', 2)
    column: Column[Any] = Connection.__dict__[key]
    if expression.startswith('~'):
        return column.ilike(expression[1:])
    elif expression.startswith('<'):
        return column < int(expression[1:])
    elif expression.startswith('>'):
        return column > int(expression[1:])
    elif isinstance(column.type, Integer):
        return column == int(expression)
    elif isinstance(column.type, Boolean):
        return column == bool(strtobool(expression))
    else:
        return column.in_(expression.split(','))
