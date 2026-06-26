"""Async StatementQueryBuilder for typed entity-repo reads."""

from __future__ import annotations
from abc import ABC
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any
from typing import cast
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import OrderByMap
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sql import row_mapping
from sqlphilosophy.sql import row_mapping_opt
from sqlphilosophy.sql import rows_mapping
from sqlphilosophy.types import RowMapping
from sqlphilosophy.types import SqlClause
from sqlphilosophy.types import SqlFilter


class _AsyncMappingResult(ABC):
    @abstractmethod
    async def all(self) -> list[RowMapping]:
        raise NotImplementedError

    @abstractmethod
    async def first(self) -> RowMapping | None:
        raise NotImplementedError

    @abstractmethod
    async def one(self) -> RowMapping:
        raise NotImplementedError


class _AsyncScalarResult[T: DeclarativeBase](ABC):
    @abstractmethod
    async def all(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    async def first(self) -> T | None:
        raise NotImplementedError


class AsyncStatementQueryBuilder[T: DeclarativeBase](ABC):
    """Fluent multi-clause async read builder (joins, filters, mappings)."""

    @abstractmethod
    def select_entity(self) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_table(self) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_columns(self, *columns: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_from(self, from_clause: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def join(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
        *,
        isouter: bool = False,
    ) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def outerjoin(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
    ) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def where(self, *criteria: SqlFilter) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def filter_by(self, **kwargs: Any) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def distinct(self, *columns: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def group_by(self, *clauses: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate(self, *from_clauses: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate_except(self, *from_clauses: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def as_lateral(self, name: str) -> SqlClause:
        raise NotImplementedError

    @abstractmethod
    def as_cte(self, name: str) -> SqlClause:
        raise NotImplementedError

    @abstractmethod
    def order_by(self, *clauses: SqlClause) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def apply_sort(
        self,
        sort: SortConfig,
        order_by: OrderByMap | None = None,
    ) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def limit(self, limit: int) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def offset(self, offset: int) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def with_for_update(
        self,
        *,
        of: SqlClause | None = None,
        skip_locked: bool = False,
    ) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def count_distinct(self, *columns: SqlClause) -> int:
        raise NotImplementedError

    @abstractmethod
    def with_params(self, params: RowMapping) -> AsyncStatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    async def scalar(self) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def mappings(self) -> _AsyncMappingResult:
        raise NotImplementedError

    @abstractmethod
    async def fetch_page(
        self,
        list_query: ListQuery,
        *,
        sort: SortConfig | None = None,
    ) -> tuple[list[RowMapping], int]:
        """Count matching rows, then return one page of row mappings."""

    @abstractmethod
    def scalars(self) -> _AsyncScalarResult[T]:
        raise NotImplementedError

    @abstractmethod
    def build_select(self) -> Select[tuple[object, ...]]:
        """Return the composed SELECT (debug/logging only; execute via builder methods)."""


class _AsyncSqlAlchemyMappingResult(_AsyncMappingResult):
    def __init__(
        self,
        session: AsyncSession,
        stmt: Select[Any],
        params: RowMapping | None = None,
    ) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    async def all(self) -> list[RowMapping]:
        result = await self._session.execute(self._stmt, cast(Mapping[str, Any], self._params))
        mapped = result.mappings()
        rows = mapped.all() if hasattr(mapped, "all") else mapped
        return rows_mapping(rows)

    async def first(self) -> RowMapping | None:
        result = await self._session.execute(
            self._stmt.limit(1), cast(Mapping[str, Any], self._params)
        )
        row = result.mappings().first()
        return row_mapping_opt(row)

    async def one(self) -> RowMapping:
        result = await self._session.execute(self._stmt, cast(Mapping[str, Any], self._params))
        row = result.mappings().one()
        return row_mapping(row)


class _AsyncSqlAlchemyScalarResult[T: DeclarativeBase](_AsyncScalarResult[T]):
    def __init__(
        self,
        session: AsyncSession,
        stmt: Select[Any],
        params: RowMapping | None = None,
    ) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    async def all(self) -> list[T]:
        result = await self._session.scalars(self._stmt, cast(Mapping[str, Any], self._params))
        return list(result.all())

    async def first(self) -> T | None:
        result = await self._session.scalars(self._stmt.limit(1), cast(Mapping[str, Any], self._params))
        return result.first()


class AsyncSqlAlchemyStatementBuilder[T: DeclarativeBase](AsyncStatementQueryBuilder[T]):
    def __init__(self, session: AsyncSession, entity_class: type[T]) -> None:
        self._session = session
        self._entity_class = entity_class
        self._stmt: Select[Any] = select(entity_class)
        self._params: RowMapping = {}

    def select_entity(self) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class)
        return self

    def select_table(self) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class.__table__)
        return self

    def select_columns(self, *columns: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = select(*columns)
        return self

    def select_from(self, from_clause: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.select_from(from_clause)
        return self

    def join(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
        *,
        isouter: bool = False,
    ) -> AsyncSqlAlchemyStatementBuilder[T]:
        if onclause is not None:
            self._stmt = self._stmt.join(target, onclause, isouter=isouter)
        else:
            self._stmt = self._stmt.join(target, isouter=isouter)
        return self

    def outerjoin(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
    ) -> AsyncSqlAlchemyStatementBuilder[T]:
        if onclause is not None:
            self._stmt = self._stmt.outerjoin(target, onclause)
        else:
            self._stmt = self._stmt.outerjoin(target)
        return self

    def where(self, *criteria: SqlFilter) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.where(*criteria)
        return self

    def filter_by(self, **kwargs: Any) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.filter_by(**kwargs)
        return self

    def distinct(self, *columns: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.distinct(*columns)
        return self

    def group_by(self, *clauses: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.group_by(*clauses)
        return self

    def correlate(self, *from_clauses: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate(*from_clauses)
        return self

    def correlate_except(self, *from_clauses: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate_except(*from_clauses)
        return self

    def as_lateral(self, name: str) -> SqlClause:
        return self._stmt.lateral(name)

    def as_cte(self, name: str) -> SqlClause:
        return self._stmt.cte(name)

    def order_by(self, *clauses: SqlClause) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.order_by(*clauses)
        return self

    def apply_sort(
        self,
        sort: SortConfig,
        order_by: OrderByMap | None = None,
    ) -> AsyncSqlAlchemyStatementBuilder[T]:
        return self.order_by(*sort.order_clauses(order_by))

    def limit(self, limit: int) -> AsyncSqlAlchemyStatementBuilder[T]:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        self._stmt = self._stmt.limit(limit)
        return self

    def offset(self, offset: int) -> AsyncSqlAlchemyStatementBuilder[T]:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        self._stmt = self._stmt.offset(offset)
        return self

    def with_for_update(
        self,
        *,
        of: SqlClause | None = None,
        skip_locked: bool = False,
    ) -> AsyncSqlAlchemyStatementBuilder[T]:
        if of is not None:
            self._stmt = self._stmt.with_for_update(of=of, skip_locked=skip_locked)
        else:
            self._stmt = self._stmt.with_for_update(skip_locked=skip_locked)
        return self

    def with_params(self, params: RowMapping) -> AsyncSqlAlchemyStatementBuilder[T]:
        self._params = {**self._params, **params}
        return self

    async def count(self) -> int:
        froms = self._stmt.get_final_froms()
        if len(froms) > 1:
            from_clause = froms[-1]  # pragma: no cover
        elif froms:
            from_clause = froms[0]
        else:
            from_clause = self._entity_class.__table__
        count_stmt = select(func.count()).select_from(from_clause)
        if self._stmt.whereclause is not None:
            count_stmt = count_stmt.where(self._stmt.whereclause)
        result = await self._session.execute(count_stmt, cast(Mapping[str, Any], self._params))
        return int(result.scalar_one() or 0)

    async def count_distinct(self, *columns: SqlClause) -> int:
        count_stmt = select(func.count(func.distinct(*columns)))
        count_stmt = count_stmt.select_from(*self._stmt.get_final_froms())
        if self._stmt.whereclause is not None:
            count_stmt = count_stmt.where(self._stmt.whereclause)
        result = await self._session.execute(count_stmt, cast(Mapping[str, Any], self._params))
        return int(result.scalar_one() or 0)

    async def scalar(self) -> Any | None:
        result = await self._session.execute(self._stmt, cast(Mapping[str, Any], self._params))
        return result.scalar_one()

    def mappings(self) -> _AsyncSqlAlchemyMappingResult:
        return _AsyncSqlAlchemyMappingResult(self._session, self._stmt, self._params)

    async def fetch_page(
        self,
        list_query: ListQuery,
        *,
        sort: SortConfig | None = None,
    ) -> tuple[list[RowMapping], int]:
        if list_query.limit < 0:
            raise ValueError("limit must be >= 0")
        if list_query.offset < 0:
            raise ValueError("offset must be >= 0")
        builder = self
        if sort is not None:
            builder = builder.apply_sort(sort, list_query.order_by)
        total = await builder.count()
        rows = await builder.limit(list_query.limit).offset(list_query.offset).mappings().all()
        return rows, total

    def scalars(self) -> _AsyncSqlAlchemyScalarResult[T]:
        return _AsyncSqlAlchemyScalarResult(self._session, self._stmt, self._params)

    def build_select(self) -> Select[tuple[object, ...]]:
        return cast(Select[tuple[object, ...]], self._stmt)
