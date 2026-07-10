"""Portable repository factory and repository protocols (no Phobos or app imports)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from sqlphilosophy.sync.repository import BaseRepository

from servicephilosophy import RepositoryFactoryProtocol, ServiceRepositoryProtocol
from sqlalchemy.orm import DeclarativeBase, Session

from sqlphilosophy.sync.query import StatementQueryBuilder
from sqlphilosophy.types import IdList, PrimaryKey, RowMapping, RowValue, SqlFilter

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R", bound="BaseRepository[Any, Any]")


class RepositoryFactory(RepositoryFactoryProtocol, Protocol):
    """Sync session-scoped factory for statement builders and entity repositories."""

    def create_statement(self, model: type[T]) -> StatementQueryBuilder[T]:
        """Return a fluent read builder for ``model``."""
        ...

    def get_repository(self, repo_class: type[R]) -> R:
        """Return a cached typed entity repository."""
        ...

    def repository(self, model: type[T]) -> BaseRepositoryProtocol[T, RepositoryFactory]:
        """Return generic CRUD helpers for ``model`` (``BaseRepository``)."""
        ...


class BaseRepositoryProtocol[T: DeclarativeBase, U: RepositoryFactory](
    ServiceRepositoryProtocol[U],
    Protocol,
):
    """SQL read/write surface for ``BaseRepository[T]``.

    Factory access (``.factory``, ``.maybe_factory``, ``.has_factory``) is inherited
    from ``ServiceRepositoryProtocol``; this protocol adds the mapped model, session,
    and SQLAlchemy CRUD/query methods only.
    """

    model: type[T]
    _session: Session

    def get(self, obj_id: PrimaryKey, load_relations: Any = None) -> T: ...

    def get_by_id(self, obj_id: PrimaryKey, load_relations: Any = None) -> T | None: ...

    def get_many(self, ids: Sequence[PrimaryKey], load_relations: Any = None) -> Sequence[T]: ...

    def first(self, load_relations: Any = None, **filters: RowValue) -> T | None: ...

    def filter(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: Any = None,
        **filters: RowValue,
    ) -> Sequence[T]: ...

    def get_all(
        self,
        *,
        page: int = 1,
        limit: int | None = None,
        load_relations: Any = None,
    ) -> Sequence[T]: ...

    def count(self, **filters: RowValue) -> int: ...

    def exists(self, obj_id: PrimaryKey) -> bool: ...

    def exists_where(self, **filters: RowValue) -> bool: ...

    def statement(self) -> StatementQueryBuilder[T]: ...

    def create(self, **fields: object) -> T: ...

    def add(self, obj: T) -> T: ...

    def get_or_create(self, *, defaults: RowMapping | None = None, **lookup: RowValue) -> tuple[T, bool]: ...

    def remove(self, obj_id: PrimaryKey) -> bool: ...

    def delete_many(self, ids: IdList) -> int: ...

    def delete_where(self, *, criteria: Sequence[SqlFilter], params: RowMapping | None = None) -> int: ...

    def update_partial(
        self,
        obj_id: PrimaryKey,
        fields: RowMapping,
        writable: frozenset[str],
        *,
        touch_updated_on: bool = False,
    ) -> int: ...

    def update_where(
        self,
        *,
        criteria: Sequence[SqlFilter],
        values: RowMapping,
        params: RowMapping | None = None,
    ) -> int: ...
