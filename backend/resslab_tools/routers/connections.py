"""
Handle /connections requests
"""
from distutils.util import strtobool
from functools import reduce
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.async_sqlalchemy import paginate
from resslab_tools.models.api import Connection as ConnectionModel
from resslab_tools.models.database import Connection
from resslab_tools.services.database import get_session
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.sqltypes import Boolean, Integer

router = APIRouter(
    prefix='/connections',
    tags=['connections'],
)


@router.get('', response_model=Page[ConnectionModel])
async def get_connections(
        session: AsyncSession = Depends(get_session),
        query: Optional[str] = Query(None),
        sortBy: List[str] = Query([]),
        sortDesc: List[bool] = Query([]),
):
    """
    Get paginated Connections
    """
    clauses: List[bool] = [query_to_clause(q)
                           for q
                           in query.split(';')] \
        if query \
        else []
    orders: List[Any] = [Connection.__dict__[key]
                         if not is_desc
                         else desc(Connection.__dict__[key])
                         for key, is_desc
                         in zip(sortBy, sortDesc)]
    select_query: Select = reduce(lambda acc, item: acc.where(item),
                                  clauses,
                                  select(Connection))
    select_query: Select = reduce(lambda acc, item: acc.order_by(item),
                                  orders,
                                  select_query)
    return await paginate(session, select_query)


def query_to_clause(query: str) -> bool:
    """
    Get where clause
    """
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
