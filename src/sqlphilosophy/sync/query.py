"""StatementQueryBuilder for typed entity-repo reads.

Default read path: ``repo.statement()`` on ``BaseRepository`` via an injected
``RepositoryFactory`` (see ``phobos.containers.repository_factory``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import Select

from sqlphilosophy.sorting import ListQuery, OrderByMap, SortConfig
from sqlphilosophy.sql import count_composed_select, row_mapping, row_mapping_opt, rows_mapping
from sqlphilosophy.types import RowMapping, SqlClause, SqlFilter


class _MappingResult(ABC):
    @abstractmethod
    def all(self) -> list[RowMapping]:
        raise NotImplementedError

    @abstractmethod
    def first(self) -> RowMapping | None:
        raise NotImplementedError

    @abstractmethod
    def one(self) -> RowMapping:
        raise NotImplementedError


class _ScalarResult[T: DeclarativeBase](ABC):
    @abstractmethod
    def all(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def first(self) -> T | None:
        raise NotImplementedError


class StatementQueryBuilder[T: DeclarativeBase](ABC):
    """Fluent multi-clause read builder (joins, filters, mappings)."""

    @abstractmethod
    def select_entity(self) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_table(self) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_columns(self, *columns: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_from(self, from_clause: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def join(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
        *,
        isouter: bool = False,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def outerjoin(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def where(self, *criteria: SqlFilter) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def filter_by(self, **kwargs: Any) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def distinct(self, *columns: SqlClause) -> StatementQueryBuilder[T]:
        """Apply row-level ``SELECT DISTINCT`` or PostgreSQL ``DISTINCT ON``.

        With no ``columns``, applies portable row-level ``SELECT DISTINCT``.
        With one or more ``columns``, delegates to SQLAlchemy's PostgreSQL
        ``DISTINCT ON`` semantics, which is not supported on all dialects.
        """
        raise NotImplementedError

    @abstractmethod
    def group_by(self, *clauses: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate(self, *from_clauses: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate_except(self, *from_clauses: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def as_lateral(self, name: str) -> SqlClause:
        raise NotImplementedError

    @abstractmethod
    def as_cte(self, name: str) -> SqlClause:
        raise NotImplementedError

    @abstractmethod
    def order_by(self, *clauses: SqlClause) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def apply_sort(
        self,
        sort: SortConfig,
        order_by: OrderByMap | None = None,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def limit(self, limit: int) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def offset(self, offset: int) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def with_for_update(
        self,
        *,
        of: SqlClause | None = None,
        skip_locked: bool = False,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_distinct(self, *columns: SqlClause) -> int:
        raise NotImplementedError

    @abstractmethod
    def with_params(self, params: RowMapping) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def scalar(self) -> Any | None:
        """Return the first column of the first row, or ``None`` when no row matches."""
        raise NotImplementedError

    @abstractmethod
    def scalar_one(self) -> Any:
        """Return exactly one scalar value; raise when zero or multiple rows match."""
        raise NotImplementedError

    @abstractmethod
    def mappings(self) -> _MappingResult:
        raise NotImplementedError

    @abstractmethod
    def fetch_page(
        self,
        list_query: ListQuery,
        *,
        sort: SortConfig | None = None,
    ) -> tuple[list[RowMapping], int]:
        """Count matching rows, then return one page of row mappings."""

    @abstractmethod
    def scalars(self) -> _ScalarResult[T]:
        raise NotImplementedError

    @abstractmethod
    def build_select(self) -> Select[tuple[object, ...]]:
        """Return the composed SELECT (debug/logging only; execute via builder methods)."""


class _SqlAlchemyMappingResult(_MappingResult):
    def __init__(self, session: Session, stmt: Select[Any], params: RowMapping | None = None) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    def all(self) -> list[RowMapping]:
        mapped = self._session.execute(self._stmt, cast(Mapping[str, Any], self._params)).mappings()
        rows = mapped.all() if hasattr(mapped, "all") else mapped
        return rows_mapping(rows)

    def first(self) -> RowMapping | None:
        row = self._session.execute(self._stmt.limit(1), cast(Mapping[str, Any], self._params)).mappings().first()
        return row_mapping_opt(row)

    def one(self) -> RowMapping:
        row = self._session.execute(self._stmt, cast(Mapping[str, Any], self._params)).mappings().one()
        return row_mapping(row)


class _SqlAlchemyScalarResult[T: DeclarativeBase](_ScalarResult[T]):
    def __init__(self, session: Session, stmt: Select[Any], params: RowMapping | None = None) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    def all(self) -> list[T]:
        return list(self._session.scalars(self._stmt, cast(Mapping[str, Any], self._params)).all())

    def first(self) -> T | None:
        return self._session.scalars(self._stmt.limit(1), cast(Mapping[str, Any], self._params)).first()


class SqlAlchemyStatementBuilder[T: DeclarativeBase](StatementQueryBuilder[T]):
    def __init__(self, session: Session, entity_class: type[T]) -> None:
        self._session = session
        self._entity_class = entity_class
        self._stmt: Select[Any] = select(entity_class)
        self._params: RowMapping = {}

    def _copy(self) -> SqlAlchemyStatementBuilder[T]:
        """Return a builder snapshot for terminal helpers that must not mutate ``self``."""
        cloned = SqlAlchemyStatementBuilder.__new__(type(self))
        cloned._session = self._session
        cloned._entity_class = self._entity_class
        cloned._stmt = self._stmt
        cloned._params = dict(self._params)
        return cloned

    def select_entity(self) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class)
        return self

    def select_table(self) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class.__table__)
        return self

    def select_columns(self, *columns: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(*columns)
        return self

    def select_from(self, from_clause: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.select_from(from_clause)
        return self

    def join(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
        *,
        isouter: bool = False,
    ) -> SqlAlchemyStatementBuilder[T]:
        if onclause is not None:
            self._stmt = self._stmt.join(target, onclause, isouter=isouter)
        else:
            self._stmt = self._stmt.join(target, isouter=isouter)
        return self

    def outerjoin(
        self,
        target: SqlClause,
        onclause: SqlClause | None = None,
    ) -> SqlAlchemyStatementBuilder[T]:
        if onclause is not None:
            self._stmt = self._stmt.outerjoin(target, onclause)
        else:
            self._stmt = self._stmt.outerjoin(target)
        return self

    def where(self, *criteria: SqlFilter) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.where(*criteria)
        return self

    def filter_by(self, **kwargs: Any) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.filter_by(**kwargs)
        return self

    def distinct(self, *columns: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        """Apply row-level ``SELECT DISTINCT`` or PostgreSQL ``DISTINCT ON``.

        With no ``columns``, applies portable row-level ``SELECT DISTINCT``.
        With one or more ``columns``, delegates to SQLAlchemy's PostgreSQL
        ``DISTINCT ON`` semantics, which is not supported on all dialects.
        """
        self._stmt = self._stmt.distinct(*columns)
        return self

    def group_by(self, *clauses: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.group_by(*clauses)
        return self

    def correlate(self, *from_clauses: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate(*from_clauses)
        return self

    def correlate_except(self, *from_clauses: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate_except(*from_clauses)
        return self

    def as_lateral(self, name: str) -> SqlClause:
        return self._stmt.lateral(name)

    def as_cte(self, name: str) -> SqlClause:
        return self._stmt.cte(name)

    def order_by(self, *clauses: SqlClause) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.order_by(*clauses)
        return self

    def apply_sort(
        self,
        sort: SortConfig,
        order_by: OrderByMap | None = None,
    ) -> SqlAlchemyStatementBuilder[T]:
        return self.order_by(*sort.order_clauses(order_by))

    def limit(self, limit: int) -> SqlAlchemyStatementBuilder[T]:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        self._stmt = self._stmt.limit(limit)
        return self

    def offset(self, offset: int) -> SqlAlchemyStatementBuilder[T]:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        self._stmt = self._stmt.offset(offset)
        return self

    def with_for_update(
        self,
        *,
        of: SqlClause | None = None,
        skip_locked: bool = False,
    ) -> SqlAlchemyStatementBuilder[T]:
        if of is not None:
            self._stmt = self._stmt.with_for_update(of=of, skip_locked=skip_locked)
        else:
            self._stmt = self._stmt.with_for_update(skip_locked=skip_locked)
        return self

    def with_params(self, params: RowMapping) -> SqlAlchemyStatementBuilder[T]:
        self._params = {**self._params, **params}
        return self

    def count(self) -> int:
        count_stmt = count_composed_select(self._stmt)
        return int(self._session.execute(count_stmt, cast(Mapping[str, Any], self._params)).scalar_one() or 0)

    def count_distinct(self, *columns: SqlClause) -> int:
        count_stmt = select(func.count(func.distinct(*columns)))
        count_stmt = count_stmt.select_from(*self._stmt.get_final_froms())
        if self._stmt.whereclause is not None:
            count_stmt = count_stmt.where(self._stmt.whereclause)
        return int(self._session.execute(count_stmt, cast(Mapping[str, Any], self._params)).scalar_one() or 0)

    def scalar(self) -> Any | None:
        """Return the first column of the first row, or ``None`` when no row matches.

        Raises ``MultipleResultsFound`` when more than one row is returned.
        """
        return self._session.execute(self._stmt, cast(Mapping[str, Any], self._params)).scalar_one_or_none()

    def scalar_one(self) -> Any:
        """Return exactly one scalar value; raise when zero or multiple rows match."""
        return self._session.execute(self._stmt, cast(Mapping[str, Any], self._params)).scalar_one()

    def mappings(self) -> _SqlAlchemyMappingResult:
        return _SqlAlchemyMappingResult(self._session, self._stmt, self._params)

    def fetch_page(
        self,
        list_query: ListQuery,
        *,
        sort: SortConfig | None = None,
    ) -> tuple[list[RowMapping], int]:
        if list_query.limit < 0:
            raise ValueError("limit must be >= 0")
        if list_query.offset < 0:
            raise ValueError("offset must be >= 0")
        builder = self._copy()
        if sort is not None:
            builder.apply_sort(sort, list_query.order_by)
        total = builder.count()
        rows = builder.limit(list_query.limit).offset(list_query.offset).mappings().all()
        return rows, total

    def scalars(self) -> _SqlAlchemyScalarResult[T]:
        return _SqlAlchemyScalarResult(self._session, self._stmt, self._params)

    def build_select(self) -> Select[tuple[object, ...]]:
        return cast(Select[tuple[object, ...]], self._stmt)


def lateral_from(select_stmt: Select[Any], name: str) -> SqlClause:
    """Return a named lateral() subquery from a Core/ORM select."""
    return select_stmt.lateral(name)


def cte_from(select_stmt: Select[Any], name: str) -> SqlClause:
    """Return a named CTE from a Core/ORM select."""
    return select_stmt.cte(name)
