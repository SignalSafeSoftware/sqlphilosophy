"""StatementQueryBuilder for typed entity-repo reads.

Default read path: ``repo.statement()`` on ``BaseRepository`` via an injected
``RepositoryFactory`` (see ``phobos.containers.repository_factory``).
"""

from __future__ import annotations
from abc import ABC
from abc import abstractmethod
from typing import cast
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import OrderByMap
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sql import row_mapping
from sqlphilosophy.sql import row_mapping_opt
from sqlphilosophy.sql import rows_mapping
from sqlphilosophy.types import RowMapping
from sqlphilosophy.types import SqlFilter


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
    def select_columns(self, *columns: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def select_from(self, from_clause: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def join(
        self,
        target: object,
        onclause: object | None = None,
        *,
        isouter: bool = False,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def outerjoin(
        self,
        target: object,
        onclause: object | None = None,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def where(self, *criteria: SqlFilter) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def filter_by(self, **kwargs: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def distinct(self, *columns: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def group_by(self, *clauses: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate(self, *from_clauses: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def correlate_except(self, *from_clauses: object) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def as_lateral(self, name: str) -> object:
        raise NotImplementedError

    @abstractmethod
    def as_cte(self, name: str) -> object:
        raise NotImplementedError

    @abstractmethod
    def order_by(self, *clauses: object) -> StatementQueryBuilder[T]:
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
        of: object | None = None,
        skip_locked: bool = False,
    ) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_distinct(self, *columns: object) -> int:
        raise NotImplementedError

    @abstractmethod
    def with_params(self, params: RowMapping) -> StatementQueryBuilder[T]:
        raise NotImplementedError

    @abstractmethod
    def scalar(self) -> object | None:
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
    def __init__(self, session: Session, stmt: object, params: RowMapping | None = None) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    def all(self) -> list[RowMapping]:
        mapped = self._session.execute(self._stmt, self._params).mappings()
        rows = mapped.all() if hasattr(mapped, "all") else mapped
        return rows_mapping(rows)

    def first(self) -> RowMapping | None:
        row = self._session.execute(self._stmt.limit(1), self._params).mappings().first()
        return row_mapping_opt(row)

    def one(self) -> RowMapping:
        row = self._session.execute(self._stmt, self._params).mappings().one()
        return row_mapping(row)


class _SqlAlchemyScalarResult[T: DeclarativeBase](_ScalarResult[T]):
    def __init__(self, session: Session, stmt: object, params: RowMapping | None = None) -> None:
        self._session = session
        self._stmt = stmt
        self._params = params or {}

    def all(self) -> list[T]:
        return list(self._session.scalars(self._stmt, self._params).all())

    def first(self) -> T | None:
        return self._session.scalars(self._stmt.limit(1), self._params).first()


class SqlAlchemyStatementBuilder[T: DeclarativeBase](StatementQueryBuilder[T]):
    def __init__(self, session: Session, entity_class: type[T]) -> None:
        self._session = session
        self._entity_class = entity_class
        self._stmt = select(entity_class)
        self._params: RowMapping = {}

    def select_entity(self) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class)
        return self

    def select_table(self) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(self._entity_class.__table__)
        return self

    def select_columns(self, *columns: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = select(*columns)
        return self

    def select_from(self, from_clause: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.select_from(from_clause)
        return self

    def join(
        self,
        target: object,
        onclause: object | None = None,
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
        target: object,
        onclause: object | None = None,
    ) -> SqlAlchemyStatementBuilder[T]:
        if onclause is not None:
            self._stmt = self._stmt.outerjoin(target, onclause)
        else:
            self._stmt = self._stmt.outerjoin(target)
        return self

    def where(self, *criteria: SqlFilter) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.where(*criteria)
        return self

    def filter_by(self, **kwargs: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.filter_by(**kwargs)
        return self

    def distinct(self, *columns: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.distinct(*columns)
        return self

    def group_by(self, *clauses: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.group_by(*clauses)
        return self

    def correlate(self, *from_clauses: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate(*from_clauses)
        return self

    def correlate_except(self, *from_clauses: object) -> SqlAlchemyStatementBuilder[T]:
        self._stmt = self._stmt.correlate_except(*from_clauses)
        return self

    def as_lateral(self, name: str) -> object:
        return self._stmt.lateral(name)

    def as_cte(self, name: str) -> object:
        return self._stmt.cte(name)

    def order_by(self, *clauses: object) -> SqlAlchemyStatementBuilder[T]:
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
        of: object | None = None,
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
        froms = self._stmt.get_final_froms()
        if len(froms) > 1:
            from_clause = froms[-1]  # pragma: no cover
        elif froms:
            from_clause = froms[0]
        else:
            from_clause = self._entity_class
        count_stmt = select(func.count()).select_from(from_clause)
        if self._stmt.whereclause is not None:
            count_stmt = count_stmt.where(self._stmt.whereclause)
        return int(self._session.execute(count_stmt, self._params).scalar_one() or 0)

    def count_distinct(self, *columns: object) -> int:
        count_stmt = select(func.count(func.distinct(*columns)))
        count_stmt = count_stmt.select_from(*self._stmt.get_final_froms())
        if self._stmt.whereclause is not None:
            count_stmt = count_stmt.where(self._stmt.whereclause)
        return int(self._session.execute(count_stmt, self._params).scalar_one() or 0)

    def scalar(self) -> object | None:
        return self._session.execute(self._stmt, self._params).scalar_one()

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
        builder = self
        if sort is not None:
            builder = builder.apply_sort(sort, list_query.order_by)
        total = builder.count()
        rows = builder.limit(list_query.limit).offset(list_query.offset).mappings().all()
        return rows, total

    def scalars(self) -> _SqlAlchemyScalarResult[T]:
        return _SqlAlchemyScalarResult(self._session, self._stmt, self._params)

    def build_select(self) -> Select[tuple[object, ...]]:
        return cast(Select[tuple[object, ...]], self._stmt)


def lateral_from(select_stmt: object, name: str) -> object:
    """Return a named lateral() subquery from a Core/ORM select."""
    return select_stmt.lateral(name)


def cte_from(select_stmt: object, name: str) -> object:
    """Return a named CTE from a Core/ORM select."""
    return select_stmt.cte(name)
