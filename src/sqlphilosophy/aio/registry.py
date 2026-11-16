"""Explicit model-to-repository construction; factories own session-scoped caching."""

from collections.abc import Callable
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.repository import AsyncBaseRepository


class AsyncRepositoryRegistry[Factory: AsyncRepositoryFactory]:
    """Resolve exact model registrations, falling back to the generic CRUD repository.

    Builders receive the caller's session and factory. The registry never opens a
    transaction, caches a repository, or infers registrations from subclasses.
    """

    def __init__(self) -> None:
        self._builders: dict[type[DeclarativeBase], object] = {}

    def register[Model: DeclarativeBase](
        self,
        model: type[Model],
        builder: Callable[[AsyncSession, Factory], AsyncBaseRepository[Model, Factory]],
    ) -> None:
        if model in self._builders:
            raise ValueError("A model already has a repository registration")
        if not callable(builder):
            raise TypeError("Repository builders must be callable")
        self._builders[model] = builder

    def repository[Model: DeclarativeBase](
        self, model: type[Model], session: AsyncSession, factory: Factory
    ) -> AsyncBaseRepository[Model, Factory]:
        registered = self._builders.get(model)
        if registered is None:
            return AsyncBaseRepository(model, session, factory)
        # register() couples this exact model key to the builder's result type.
        builder = cast(Callable[[AsyncSession, Factory], AsyncBaseRepository[Model, Factory]], registered)
        repository = builder(session, factory)
        if not isinstance(repository, AsyncBaseRepository):
            raise TypeError("Repository builders must return a AsyncBaseRepository")
        if repository.model is not model or repository.session is not session or repository.factory is not factory:
            raise ValueError("Repository construction changed its model, session or factory")
        return repository
