"""Async AsyncBaseRepository behavior."""

from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from conftest import Widget
from conftest import WidgetTag
from sqlalchemy.ext.asyncio import AsyncSession
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository


class _OtherAsyncRepo(AsyncBaseRepository[Widget]):
    def __init__(self, session: AsyncSession, factory: AsyncRepositoryFactory) -> None:
        super().__init__(Widget, session, factory)


class _FakeAsyncFactory(AsyncRepositoryFactory):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.created: list[type] = []

    @property
    def session(self) -> AsyncSession:
        return self._session

    def create_statement(self, model: type) -> AsyncSqlAlchemyStatementBuilder:
        self.created.append(model)
        return AsyncSqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type):
        return repo_class(self._session, self)


@pytest.mark.asyncio
async def test_async_create_get(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    created = await repo.create(name="async")
    assert created.id is not None
    assert await repo.get_by_id(created.id) is created
    assert (await repo.get(created.id)).name == "async"


@pytest.mark.asyncio
async def test_async_get_many_filter_count(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    a = await repo.create(name="a", active=True)
    await repo.create(name="b", active=False)
    assert len(await repo.get_many([a.id])) == 1
    assert await repo.get_many([]) == []
    assert await repo.count(active=True) == 1
    assert len(await repo.filter(active=True)) == 1


@pytest.mark.asyncio
async def test_async_delete_many(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="del")
    assert await repo.remove(row.id) is True
    one = await repo.create(name="x")
    two = await repo.create(name="y")
    assert await repo.delete_many([one.id, two.id]) == 2


@pytest.mark.asyncio
async def test_async_statement_without_factory(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    builder = repo.statement()
    assert isinstance(builder, AsyncSqlAlchemyStatementBuilder)


@pytest.mark.asyncio
async def test_async_for_repo_without_factory_raises(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(RuntimeError, match="AsyncRepositoryFactory"):
        repo.for_repo(_OtherAsyncRepo)


@pytest.mark.asyncio
async def test_async_for_repo_with_factory(async_session: AsyncSession) -> None:
    factory = _FakeAsyncFactory(async_session)
    repo = AsyncBaseRepository(Widget, async_session, factory)
    other = repo.for_repo(_OtherAsyncRepo)
    assert isinstance(other, _OtherAsyncRepo)


def test_async_composite_pk_rejected() -> None:
    with pytest.raises(TypeError, match="single-column primary key"):
        AsyncBaseRepository(WidgetTag, MagicMock())


@pytest.mark.asyncio
async def test_async_extended_helpers(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="ext")
    assert await repo.exists(row.id)
    assert await repo.exists_where(name="ext")
    obj, created = await repo.get_or_create(name="new-async")
    assert created is True
    again, created2 = await repo.get_or_create(name="new-async")
    assert created2 is False
    assert again.id == obj.id
    updated = await repo.update_partial(row.id, {"name": "changed"}, frozenset({"name"}))
    assert updated == 1
    deleted = await repo.delete_where(criteria=[Widget.name == "changed"])
    assert deleted == 1
    names = await repo.list_table_names()
    assert "widget" in names
    assert await repo.has_table("widget")
