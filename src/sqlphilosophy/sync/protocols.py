"""Portable repository factory protocol (no Phobos or app imports)."""

from __future__ import annotations
from typing import Protocol
from typing import TypeVar
from sqlalchemy.orm import DeclarativeBase
from sqlphilosophy.sync.query import StatementQueryBuilder

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R")


class RepositoryFactory(Protocol):
    """Session-scoped factory for statement builders and entity repositories."""

    def create_statement(self, model: type[T]) -> StatementQueryBuilder[T]:
        """Return a fluent read builder for ``model``."""
        ...

    def get_repository(self, repo_class: type[R]) -> R:
        """Return a cached typed entity repository."""
        ...

    def repository(self, model: type[T]) -> object:
        """Return generic CRUD helpers for ``model`` (``BaseRepository`` in Phobos)."""
        ...
