"""
Handle /connections requests
"""
from functools import reduce
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.async_sqlalchemy import paginate
from resslab_tools.models.api import Connection as ConnectionModel
from resslab_tools.models.database import Connection
from resslab_tools.services.database import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.selectable import Select

router = APIRouter(
    prefix='/connections',
    tags=['connections'],
)


@router.get('', response_model=Page[ConnectionModel])
async def get_connections(
        session: AsyncSession = Depends(get_session),
        query: Optional[str] = Query(None)):
    """
    Get paginated Connections
    """
    if query:
        clauses: List[bool] = [query_to_clause(q) for q in query.split(';')]
    else:
        clauses = []
    select_query: Select = reduce(lambda acc, item: acc.where(item),
                                  clauses,
                                  select(Connection))
    return await paginate(session, select_query)


def query_to_clause(query: str) -> bool:
    key, expression = query.split(':', 2)
    column: Column[Any] = Connection.__dict__[key]
    if expression.startswith('~'):
        return column.like(f'%{expression[1:]}%')
    elif expression.startswith('!'):
        return column.notin_(expression[1:].split(','))
    else:
        return column.in_(expression.split(','))
