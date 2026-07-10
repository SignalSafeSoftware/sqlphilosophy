"""Protocol layering: servicephilosophy factory surface + SQL repository methods."""

from __future__ import annotations

from servicephilosophy import RepositoryFactoryProtocol, ServiceRepositoryProtocol
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Widget
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


class _FakeFactory(RepositoryFactory):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_statement(self, model: type) -> SqlAlchemyStatementBuilder:
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type):
        return repo_class(self._session, self)

    def repository(self, model: type):
        return BaseRepository(model, self._session, self)


class _FakeAsyncFactory(AsyncRepositoryFactory):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def create_statement(self, model: type) -> AsyncSqlAlchemyStatementBuilder:
        return AsyncSqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type):
        return repo_class(self._session, self)

    def repository(self, model: type):
        return AsyncBaseRepository(model, self._session, self)


def _accept_service_repo(repo: ServiceRepositoryProtocol[RepositoryFactory]) -> bool:
    return repo.has_factory


def _accept_sql_factory(factory: RepositoryFactoryProtocol) -> bool:
    return hasattr(factory, "create_statement")


def test_sync_repository_inherits_service_factory_protocol(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    assert _accept_service_repo(repo) is True
    assert repo.model is Widget
    assert repo._session is sync_session
    assert repo.factory is factory
    assert repo.maybe_factory is factory


def test_sync_factory_extends_repository_factory_protocol(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    assert _accept_sql_factory(factory) is True
    generic = factory.repository(Widget)
    assert isinstance(generic, BaseRepository)
    builder = factory.create_statement(Widget)
    assert isinstance(builder, SqlAlchemyStatementBuilder)


async def test_async_repository_inherits_service_factory_protocol(async_session: AsyncSession) -> None:
    factory = _FakeAsyncFactory(async_session)
    repo = AsyncBaseRepository(Widget, async_session, factory)

    def _accept_async_service(repo: ServiceRepositoryProtocol[AsyncRepositoryFactory]) -> bool:
        return repo.has_factory

    assert _accept_async_service(repo) is True
    assert repo.model is Widget
    assert repo._session is async_session
    assert repo.factory is factory
    assert repo.maybe_factory is factory


async def test_async_factory_extends_repository_factory_protocol(async_session: AsyncSession) -> None:
    factory = _FakeAsyncFactory(async_session)
    assert _accept_sql_factory(factory) is True
    generic = factory.repository(Widget)
    assert isinstance(generic, AsyncBaseRepository)
    builder = factory.create_statement(Widget)
    assert isinstance(builder, AsyncSqlAlchemyStatementBuilder)
