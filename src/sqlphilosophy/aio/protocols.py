"""Portable async repository factory protocol (no Phobos or app imports)."""

from __future__ import annotations
from typing import Protocol
from typing import TypeVar
from sqlalchemy.orm import DeclarativeBase
from sqlphilosophy.aio.query import AsyncStatementQueryBuilder

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R")


class AsyncRepositoryFactory(Protocol):
    """Session-scoped factory for async statement builders and entity repositories."""

    def create_statement(self, model: type[T]) -> AsyncStatementQueryBuilder[T]:
        """Return a fluent async read builder for ``model``."""
        ...

    def get_repository(self, repo_class: type[R]) -> R:
        """Return a cached typed entity repository."""
        ...

    def repository(self, model: type[T]) -> object:
        """Return generic CRUD helpers for ``model`` (``AsyncBaseRepository`` in Phobos)."""
        ...
