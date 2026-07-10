"""Portable async repository factory and repository protocols (no Phobos or app imports)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from sqlphilosophy.aio.repository import AsyncBaseRepository

from servicephilosophy import RepositoryFactoryProtocol, ServiceRepositoryProtocol
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from sqlphilosophy.aio.query import AsyncStatementQueryBuilder
from sqlphilosophy.types import IdList, PrimaryKey, RowMapping, RowValue, SqlFilter

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R", bound="AsyncBaseRepository[Any, Any]")


class AsyncRepositoryFactory(RepositoryFactoryProtocol, Protocol):
    """Async session-scoped factory for statement builders and entity repositories."""

    def create_statement(self, model: type[T]) -> AsyncStatementQueryBuilder[T]:
        """Return a fluent async read builder for ``model``."""
        ...

    def get_repository(self, repo_class: type[R]) -> R:
        """Return a cached typed entity repository."""
        ...

    def repository(self, model: type[T]) -> AsyncBaseRepositoryProtocol[T, AsyncRepositoryFactory]:
        """Return generic CRUD helpers for ``model`` (``AsyncBaseRepository``)."""
        ...


class AsyncBaseRepositoryProtocol[T: DeclarativeBase, U: AsyncRepositoryFactory](
    ServiceRepositoryProtocol[U],
    Protocol,
):
    """Async SQL read/write surface for ``AsyncBaseRepository[T]``.

    Factory access (``.factory``, ``.maybe_factory``, ``.has_factory``) is inherited
    from ``ServiceRepositoryProtocol``; this protocol adds the mapped model, session,
    and SQLAlchemy CRUD/query methods only.
    """

    model: type[T]
    _session: AsyncSession

    async def get(self, obj_id: PrimaryKey, load_relations: Any = None) -> T: ...

    async def get_by_id(self, obj_id: PrimaryKey, load_relations: Any = None) -> T | None: ...

    async def get_many(self, ids: Sequence[PrimaryKey], load_relations: Any = None) -> Sequence[T]: ...

    async def first(self, load_relations: Any = None, **filters: RowValue) -> T | None: ...

    async def filter(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: Any = None,
        **filters: RowValue,
    ) -> Sequence[T]: ...

    async def get_all(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: Any = None,
    ) -> Sequence[T]: ...

    async def count(self, **filters: RowValue) -> int: ...

    async def exists(self, obj_id: PrimaryKey) -> bool: ...

    async def exists_where(self, **filters: RowValue) -> bool: ...

    def statement(self) -> AsyncStatementQueryBuilder[T]: ...

    async def create(self, **fields: object) -> T: ...

    async def add(self, obj: T) -> T: ...

    async def get_or_create(self, *, defaults: RowMapping | None = None, **lookup: RowValue) -> tuple[T, bool]: ...

    async def remove(self, obj_id: PrimaryKey) -> bool: ...

    async def delete_many(self, ids: IdList) -> int: ...

    async def delete_where(self, *, criteria: Sequence[SqlFilter], params: RowMapping | None = None) -> int: ...

    async def update_partial(
        self,
        obj_id: PrimaryKey,
        fields: RowMapping,
        writable: frozenset[str],
        *,
        touch_updated_on: bool = False,
    ) -> int: ...

    async def update_where(
        self,
        *,
        criteria: Sequence[SqlFilter],
        values: RowMapping,
        params: RowMapping | None = None,
    ) -> int: ...
