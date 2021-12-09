"""
https://uriyyo-fastapi-pagination.netlify.app/customization/
"""
from typing import Generic, TypeVar

from fastapi import Query
from fastapi_pagination.default import Page, Params

T = TypeVar("T")


class ExtendedParams(Params):
    size: int = Query(50, ge=1, le=1000, description="Page size")


class ExtendedPage(Page[T], Generic[T]):
    __params_type__ = ExtendedParams
