"""
https://uriyyo-fastapi-pagination.netlify.app/customization/
"""

from typing import Any, Callable, Generic, Optional, TypeVar

from fastapi import Query
from fastapi_pagination.api import resolve_params
from fastapi_pagination.bases import AbstractParams
from fastapi_pagination.default import Page, Params
from fastapi_pagination.ext.sqlalchemy import create_paginate_query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class ExtendedParams(Params):
    size: int = Query(10, ge=1, le=1000, description="Page size")


class ExtendedPage(Page[T], Generic[T]):
    __params_type__ = ExtendedParams
    total: int


async def paginate(
    session: AsyncSession,
    query: Select,
    map_value: Callable[[Any], Any],
    params: Optional[AbstractParams] = None,
    count_query: Optional[Select] = None,
) -> Page[T]:
    params = resolve_params(params)

    # When the row query carries expensive per-row column_property subqueries
    # (e.g. the *_count fields), wrapping it in COUNT(*) forces those subqueries
    # to run for every row in the table. Callers can pass a cheap equivalent
    # count_query (COUNT(*) over the filtered table) to avoid that.
    if count_query is None:
        count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    result = await session.execute(create_paginate_query(query, params))
    items = result.unique().all()
    mapped_items = [
        {k: map_value(v) for k, v in item._mapping.items()} for item in items
    ]

    # Items stay plain dicts: the route's response_model validates them once on
    # the way out. Building Pydantic models here would validate everything twice.
    return ExtendedPage.create(
        items=mapped_items,
        params=params,
        total=total,
    )
