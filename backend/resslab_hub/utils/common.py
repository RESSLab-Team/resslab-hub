from abc import ABC
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import reduce
from math import ceil, isnan
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, Union

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from pydantic.main import BaseModel
from sqlalchemy import and_, desc, distinct, func, inspect, not_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BooleanClauseList, ColumnElement
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.sqltypes import Boolean, Date, Float, Integer, Numeric, String

from resslab_hub.data.not_reported import NOT_REPORTED_COLUMN
from resslab_hub.models.api import (
    CountModel,
    DateRangeModel,
    FieldsModel,
    MatrixModel,
    RangeModel,
)
from resslab_hub.utils.database import Base, async_session
from resslab_hub.utils.fastapi import HttpHeader, MediaType, attachment
from resslab_hub.utils.pagination import paginate

D = TypeVar("D", bound=Base)  # type: ignore
M = TypeVar("M", bound=BaseModel)


# Replacement for distutils.util.strtobool (removed in Python 3.12).
def strtobool(value: str) -> int:
    v = value.lower()
    if v in ("y", "yes", "t", "true", "on", "1"):
        return 1
    if v in ("n", "no", "f", "false", "off", "0"):
        return 0
    raise ValueError(f"invalid truth value {value!r}")


class SubComponent:
    def __init__(
        self,
        name: str,
        parent_id_column: Column[str],
        id_column: Column[int],
        columns: Dict[Column[Numeric], str],
    ) -> None:
        self.name = name
        self.parent_id_column = parent_id_column
        self.id_column = id_column
        self.columns = list(columns.keys())
        self.column_names = list(columns.values())

    async def get_series(
        self,
        session: AsyncSession,
        parent_id: str,
        size: int,
    ) -> List[List[float]]:
        return await Component.get_series(
            session,
            select(*self.columns)
            .where(self.parent_id_column == parent_id)
            .order_by(self.id_column),
            self.id_column,
            size,
        )

    async def get_csv(
        self,
        session: AsyncSession,
        parent_id: str,
    ) -> StreamingResponse:
        filename = f"{self.name}-{parent_id}.csv"
        return Component.get_csv_response(
            session,
            select(*self.columns)
            .where(self.parent_id_column == parent_id)
            .order_by(self.id_column),
            self.column_names,
            filename,
        )


class Component(ABC, Generic[D, M]):
    def __init__(
        self,
        name: str,
        database_type: type[D],
        model_type: type[M],
        id_column: Column[str],
        ignored_columns: Set[Column],
    ) -> None:
        self.name = name
        self.database_type = database_type
        self.model_type = model_type
        self.id_column = id_column
        self.ignored_columns = ignored_columns

        model_keys: Set[str] = set(model_type.model_fields.keys())
        self.model_columns: Dict[str, Column] = {
            key: column
            for key, column in database_type.__dict__.items()
            if key in model_keys
        }
        self.all_columns: Dict[str, Column] = {
            key: column
            for key, column in database_type.__dict__.items()
            if not key.startswith("_") and column not in ignored_columns
        }
        # What `query` and `sort_by` may name: the mapped columns, nothing
        # else. A bare `__dict__` lookup also reached `__class__` or
        # `metadata`, and an unknown key was a KeyError, so a 500 (#264 M7).
        self.queryable_columns: Dict[str, Column] = {
            attr.key: getattr(database_type, attr.key)
            for attr in inspect(database_type).column_attrs
        }

    async def get_page(
        self,
        session: AsyncSession,
        query: Optional[str],
        sort_by: List[str],
        sort_desc: List[bool],
    ) -> Page[M]:
        where_clauses = self.__get_where_clauses(query)
        # Check every key first: the zip below stops at the shorter list, so a
        # key with no `sort_desc` would never be looked at.
        sort_columns = [self.__get_column(key) for key in sort_by]
        order_clauses = [
            desc(column) if is_desc else column
            for column, is_desc in zip(sort_columns, sort_desc)
        ]
        page = await paginate(
            session,
            select(*self.model_columns.values())
            .where(and_(*where_clauses))
            .order_by(*order_clauses),
            self.__get_non_nan,
            count_query=select(func.count())
            .select_from(self.database_type)
            .where(and_(*where_clauses)),
        )
        return page

    async def get_fields(
        self,
        session: AsyncSession,
        fields: List[str],
    ) -> List[FieldsModel]:
        columns = [self.database_type.__dict__[field] for field in fields]
        rows = await session.execute(select(*columns).select_from(self.database_type))
        return [
            {k: self.__get_non_nan(v) for k, v in row._mapping.items()} for row in rows
        ]

    async def get_counts(
        self,
        session: AsyncSession,
        fields: List[str],
        query: Optional[str],
    ) -> List[CountModel]:
        where_clauses = self.__get_where_clauses(query)
        columns = [self.database_type.__dict__[field] for field in fields]
        rows = await session.execute(
            select(*columns, func.count())
            .select_from(self.database_type)
            .where(and_(*where_clauses))
            .group_by(*columns)
        )
        return [
            CountModel(
                names=[str(self.__format_value(value)) for value in list(row)[:-1]],
                value=row[-1],
            )
            for row in rows
        ]

    async def get_range(
        self,
        session: AsyncSession,
        number_field: str,
    ) -> RangeModel:
        """
        Get range of field
        """
        column: Column[Union[Float, Integer, Numeric]] = self.__get_column(number_field)
        rows = await session.execute(select(func.min(column), func.max(column)))
        row = next(rows)
        # Postgres sorts NaN above every number, so max() over a column with
        # NaN sentinels returns NaN; RangeModel maps that to None.
        return RangeModel(
            min=self.__get_non_nan(row[0]), max=self.__get_non_nan(row[1])
        )

    async def get_date_range(
        self,
        session: AsyncSession,
        date_field: str,
    ) -> DateRangeModel:
        """
        Get range of field
        """
        column: Column[Date] = self.__get_column(date_field)
        rows = await session.execute(select(func.min(column), func.max(column)))
        row = next(rows)
        return DateRangeModel(min=row[0], max=row[1])

    async def get_matrix(
        self,
        session: AsyncSession,
        fields: List[str],
        query: Optional[str],
    ) -> MatrixModel:
        where_clauses = self.__get_where_clauses(query)
        columns = [self.__get_column(field) for field in fields]
        rows = await session.execute(
            select(self.id_column, *columns).where(and_(*where_clauses))
        )
        rows = rows.all()
        ids = [row[0] for row in rows]
        data = [[self.__clean_value(value) for value in list(row)[1:]] for row in rows]
        return MatrixModel(ids=ids, data=data)

    async def get_csv(
        self,
        session: AsyncSession,
        ids: List[str],
    ) -> StreamingResponse:
        time = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{self.name}-{time}.csv"
        # The `not_reported` list is not written as a column: it is selected
        # last and turns its NULL cells into `NR`, like the source CSV (#427).
        columns = {
            key: column
            for key, column in self.model_columns.items()
            if key != NOT_REPORTED_COLUMN
        }
        not_reported = self.model_columns.get(NOT_REPORTED_COLUMN)
        selected = [*columns.values()]
        if not_reported is not None:
            selected.append(not_reported)
        return self.get_csv_response(
            session,
            select(*selected).where(self.id_column.in_(ids)),
            list(columns.keys()),
            filename,
            with_not_reported=not_reported is not None,
        )

    async def get_distinct(self, session: AsyncSession, fields: List[str]) -> int:
        columns = [self.database_type.__dict__[field] for field in fields]
        count = await session.scalar(
            select(
                func.count(distinct(tuple_(*columns)))
                if len(columns) > 0
                else func.count()
            ).select_from(self.database_type)
        )
        return count or 0

    def get_sub(
        self,
        name: str,
        parent_id_column: Column[str],
        id_column: Column[int],
        columns: Dict[Column[Numeric], str],
    ) -> SubComponent:
        return SubComponent(
            f"{self.name}-{name}",
            parent_id_column,
            id_column,
            columns,
        )

    @staticmethod
    async def get_series(
        session: AsyncSession,
        statement: Select,
        id_column: Column[int],
        size: int,
    ) -> List[List[float]]:
        if size > 0:
            count: Optional[int] = await session.scalar(
                select(func.count()).select_from(statement.subquery())
            )
            if not count:
                return []
            if count > size:
                n = ceil(float(count) / float(size))
                statement = statement.where(func.mod(id_column, n) == 0)
        rows = await session.execute(statement)
        rows = list(rows)

        if rows and len(rows[0]) == 1:
            return [[row[0]] for row in rows]
        else:
            return [[row[0], row[1]] for row in rows]

    @staticmethod
    def get_csv_response(
        session: AsyncSession,
        statement: Select,
        headers: List[str],
        filename: str,
        with_not_reported: bool = False,
    ) -> StreamingResponse:
        # The request-scoped `session` is closed as soon as this handler returns
        # the StreamingResponse, before the body generator runs. The generator
        # therefore opens and owns its own session (see __get_csv_stream).
        return StreamingResponse(
            Component.__get_csv_stream(
                statement,
                headers,
                with_not_reported=with_not_reported,
            ),
            headers={HttpHeader.CONTENT_DISPOSITION.value: attachment(filename)},
            media_type=MediaType.CSV.value,
        )

    @staticmethod
    def __clean_value(value: Any) -> Optional[Union[Decimal, float, str]]:
        if isinstance(value, (float, Decimal)) and isnan(value):
            return None
        return value

    def __get_column(self, key: str) -> Column[Any]:
        column = self.queryable_columns.get(key)
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown column: {key}",
            )
        return column

    def __get_where_clauses(
        self, query: Optional[str]
    ) -> List[Union[BooleanClauseList, ColumnElement]]:
        """
        Get where clauses
        """
        return [self.__get_where_clause(q) for q in query.split(";")] if query else []

    def __get_where_clause(self, query: str) -> Union[BooleanClauseList, ColumnElement]:
        """
        Get where clause
        """
        if ":" not in query:
            return self.__get_global_predicate(query)
        # Split once: the value itself may hold a colon.
        key, expression = query.split(":", 1)
        column: Column[Any] = self.__get_column(key)
        return self.__get_predicate(column, expression)

    def __get_global_predicate(self, expression: str) -> BooleanClauseList:
        if expression.startswith("!"):
            predicates = [
                column.cast(String).not_ilike(expression[1:])
                for column in self.model_columns.values()
                if column not in self.ignored_columns
            ]
        else:
            predicates = [
                column.cast(String).ilike(expression)
                for column in self.model_columns.values()
                if column not in self.ignored_columns
            ]
        return reduce(
            lambda a, b: a | b,
            predicates,
        )

    @staticmethod
    def __cast(column: Column[Any], text: str) -> Any:
        """The value of a filter, typed like its column.

        A value that does not parse is the caller's mistake: 400, not 500.
        """
        try:
            if isinstance(column.type, Integer):
                return int(text)
            if isinstance(column.type, Numeric):
                return Decimal(text)
            if isinstance(column.type, Date):
                return date.fromisoformat(text)
            if isinstance(column.type, Boolean):
                return bool(strtobool(text))
        except (ValueError, InvalidOperation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bad value for {column.key}: {text}",
            )
        return text

    @staticmethod
    def __get_predicate(
        column: Column[Any], expression: str
    ) -> Union[BooleanClauseList, ColumnElement]:
        cast = Component.__cast
        if expression.startswith("!"):
            return not_(Component.__get_predicate(column, expression[1:]))
        if "," in expression:
            return column.in_([cast(column, value) for value in expression.split(",")])
        if "<<" in expression and isinstance(column.type, (Integer, Numeric, Date)):
            min, max = expression.split("<<", 1)
            return column.between(cast(column, min), cast(column, max))
        if expression.startswith("<"):
            return column < cast(column, expression[1:])
        if expression.startswith(">"):
            return column > cast(column, expression[1:])
        if isinstance(column.type, String):
            return column.ilike(f"%{expression}%")
        return column == cast(column, expression)

    @staticmethod
    def __format_value(
        value: Optional[Union[str, float, Decimal]],
    ) -> Union[str, Decimal]:
        if value is None:
            return "NA"
        if isinstance(value, float):
            # Go through Decimal so floats keep the historical CSV/counts
            # formatting (normalize drops trailing zeros: 300.0 -> "300").
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            if isnan(value):
                return "NR"
            return Decimal(f"{value.normalize():f}")  # noqa: E231
        return value

    @staticmethod
    def __get_non_nan(value: Any) -> Any:
        if isinstance(value, (float, Decimal)) and isnan(value):
            return None
        else:
            return value

    @staticmethod
    async def __get_csv_stream(
        statement: Select,
        headers: List[str],
        partition_size=128,
        separator=",",
        with_not_reported: bool = False,
    ):
        """
        With `with_not_reported`, the last item of each row is its
        `not_reported` list: a NULL cell of a listed column is written `NR`,
        the other NULL cells `NA`.
        """
        yield separator.join(headers) + "\n"
        # Own a dedicated session: the request-scoped one is already closed by
        # the time Starlette consumes this generator.
        async with async_session() as session:
            result = await session.stream(statement)
            async for partition in result.partitions(partition_size):  # type: ignore
                for row in partition:
                    items = list(row)
                    listed = set(items.pop() or []) if with_not_reported else set()
                    yield (
                        separator.join(
                            [
                                "NR"
                                if item is None and name in listed
                                else str(Component.__format_value(item))
                                for name, item in zip(headers, items)
                            ]
                        )
                        + "\n"
                    )
