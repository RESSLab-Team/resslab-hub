from abc import ABC
from datetime import datetime
from decimal import Decimal
from distutils.util import strtobool
from math import ceil, isnan
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, Union

from fastapi.responses import StreamingResponse
from fastapi_pagination.default import Page
from pydantic.main import BaseModel
from sqlalchemy import and_, desc, distinct, func, not_, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import column_property
from sqlalchemy.sql.elements import BooleanClauseList, ColumnElement
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.sqltypes import BigInteger, Boolean, Float, Integer, Numeric, String

from resslab_hub.models.api import CountModel, MatrixModel, RangeModel
from resslab_hub.utils.database import Base
from resslab_hub.utils.fastapi import HttpHeader, MediaType, attachment
from resslab_hub.utils.pagination import paginate

D = TypeVar("D", bound=Base)  # type: ignore
M = TypeVar("M", bound=BaseModel)


class SubComponent:
    def __init__(
        self,
        name: str,
        parent_id_column: Column[String],
        id_column: Column[BigInteger],
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
    ) -> List[List[Decimal]]:
        return await Component.get_series(
            session,
            select(self.columns)
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
            select(self.columns)
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
        id_column: Column[String],
        ignored_columns: Set[column_property],
    ) -> None:
        self.name = name
        self.database_type = database_type
        self.model_type = model_type
        self.id_column = id_column
        self.ignored_columns = ignored_columns

        model_keys: Set[str] = set(model_type.__fields__.keys())
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

    async def get_page(
        self,
        session: AsyncSession,
        query: Optional[str],
        sort_by: List[str],
        sort_desc: List[bool],
    ) -> Page[M]:
        where_clauses = self.__get_where_clauses(query)
        order_clauses = [
            desc(self.__get_column(key)) if is_desc else self.__get_column(key)
            for key, is_desc in zip(sort_by, sort_desc)
        ]
        page = await paginate(
            session,
            select(*self.model_columns.values())
            .where(and_(*where_clauses))
            .order_by(*order_clauses),
            self.model_type,
            self.__get_non_nan,
        )
        return page

    async def get_counts(
        self,
        session: AsyncSession,
        fields: List[str],
        query: Optional[str],
    ) -> List[CountModel]:
        where_clauses = self.__get_where_clauses(query)
        columns = [self.database_type.__dict__[field] for field in fields]
        rows = await session.execute(
            select([*columns, func.count()])
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
        rows = await session.execute(select([func.min(column), func.max(column)]))
        row = next(rows)
        return RangeModel(min=row[0], max=row[1])

    async def get_matrix(
        self,
        session: AsyncSession,
        fields: List[str],
        query: Optional[str],
    ) -> MatrixModel:
        where_clauses = self.__get_where_clauses(query)
        columns = [self.__get_column(field) for field in fields]
        rows = await session.execute(
            select([self.id_column, *columns]).where(and_(*where_clauses))
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
        return self.get_csv_response(
            session,
            select(self.model_columns.values()).where(self.id_column.in_(ids)),
            list(self.model_columns.keys()),
            filename,
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
        return count

    def get_sub(
        self,
        name: str,
        parent_id_column: Column[String],
        id_column: Column[BigInteger],
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
        id_column: Column[BigInteger],
        size: int,
    ) -> List[List[Decimal]]:
        if size > 0:
            count: int = await session.scalar(
                select(func.count()).select_from(statement)
            )
            if count == 0:
                return []
            if count > size:
                n = ceil(float(count) / float(size))
                statement = statement.where(func.mod(id_column, n) == 0)
        rows = await session.execute(statement)
        return [[row[0], row[1]] for row in rows]

    @staticmethod
    def get_csv_response(
        session: AsyncSession,
        statement: Select,
        headers: List[str],
        filename: str,
    ) -> StreamingResponse:
        return StreamingResponse(
            Component.__get_csv_stream(
                session,
                statement,
                headers,
            ),
            headers={HttpHeader.CONTENT_DISPOSITION.value: attachment(filename)},
            media_type=MediaType.CSV.value,
        )

    @staticmethod
    def __clean_value(value: Any) -> Optional[Union[Decimal, str]]:
        if type(value) == Decimal and isnan(value):
            return None
        return value

    def __get_column(self, key: str) -> Column[Any]:
        return self.database_type.__dict__[key]

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
        key, expression = query.split(":", 2)
        column: Column[Any] = self.__get_column(key)
        return self.__get_predicate(column, expression)

    def __get_global_predicate(self, expression: str) -> BooleanClauseList:
        if expression.startswith("!"):
            return or_(
                *[
                    column.cast(String).not_ilike(expression[1:])
                    for column in self.model_columns.values()
                    if column not in self.ignored_columns
                ]
            )
        else:
            return or_(
                *[
                    column.cast(String).ilike(expression)
                    for column in self.model_columns.values()
                    if column not in self.ignored_columns
                ]
            )

    @staticmethod
    def __get_predicate(
        column: Column[Any], expression: str
    ) -> Union[BooleanClauseList, ColumnElement]:
        if expression.startswith("!"):
            return not_(Component.__get_predicate(column, expression[1:]))
        if "," in expression:
            return column.in_(expression.split(","))
        if "<<" in expression:
            [min, max] = expression.split("<<", 2)
            return column.between(Decimal(min), Decimal(max))
        if expression.startswith("<"):
            return column < int(expression[1:])
        if expression.startswith(">"):
            return column > int(expression[1:])
        if isinstance(column.type, String):
            return column.ilike(expression)
        if isinstance(column.type, Integer):
            return column == int(expression)
        if isinstance(column.type, Numeric):
            return column == Decimal(expression)
        if isinstance(column.type, Boolean):
            return column == bool(strtobool(expression))
        return column == expression

    @staticmethod
    def __format_value(value: Optional[Union[str, Decimal]]) -> Union[str, Decimal]:
        if value is None:
            return "NA"
        if isinstance(value, Decimal):
            if isnan(value):
                return "NR"
            return Decimal(f"{value.normalize():f}")
        return value

    @staticmethod
    def __get_non_nan(value: Any) -> Any:
        if isinstance(value, Decimal) and isnan(value):
            return None
        else:
            return value

    @staticmethod
    async def __get_csv_stream(
        session: AsyncSession,
        statement: Select,
        headers: List[str],
        partition_size=128,
        separator=",",
    ):
        yield separator.join(headers) + "\n"
        result = await session.stream(statement)
        async for partition in result.partitions(partition_size):  # type: ignore
            for row in partition:
                yield separator.join(
                    [str(Component.__format_value(item)) for item in row]
                ) + "\n"
