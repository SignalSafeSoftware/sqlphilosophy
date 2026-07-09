"""Async AsyncBaseRepository behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load

from conftest import Tag, UpdatableTag, Widget, WidgetTag
from sqlphilosophy._repository_shared import PartialUpdatePlan
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec


class _OtherAsyncRepo(AsyncBaseRepository[Widget, AsyncRepositoryFactory]):
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


async def test_list_table_names_without_inspector(async_session, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = AsyncBaseRepository(Widget, async_session)

    def _no_inspect(_conn: object) -> None:
        return None

    monkeypatch.setattr("sqlphilosophy.aio.repository.sa_inspect", _no_inspect)
    assert await repo.list_table_names() == frozenset()


@pytest.mark.asyncio
async def test_async_batched_purge_ids(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="b1")
    await repo.create(name="b2")
    total = await repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=1)
    assert total == 2


@pytest.mark.asyncio
async def test_async_batched_purge_ids_rejects_invalid_batch_size(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="b1")
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        await repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=0)
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        await repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=-1)
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_async_get_raises_lookup_for_missing_id(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(LookupError):
        await repo.get(99999)


@pytest.mark.asyncio
async def test_async_get_many_with_load_relations(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="rem")
    loaded = await repo.get_many([row.id], load_relations=[Load(Widget)])
    assert len(loaded) == 1


@pytest.mark.asyncio
async def test_async_fetch_mappings_page_rejects_negative_limits(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await repo.fetch_mappings_page(select(Widget.id), limit=-1, offset=0)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        await repo.fetch_mappings_page(select(Widget.id), limit=1, offset=-1)


@pytest.mark.asyncio
async def test_async_update_where_and_delete_where_guards(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="left")
    await repo.create(name="delete-params")
    assert await repo.delete_where(criteria=[Widget.name == "delete-params"], params={"p": 1}) == 1
    assert await repo.update_where(criteria=[Widget.id == row.id], values={}) == 0
    assert await repo.delete_where(criteria=[]) == 0


@pytest.mark.asyncio
async def test_async_get_with_join_and_update_where(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    widget = await repo.create(name="async-ext")
    await AsyncBaseRepository(Tag, async_session).create(label="t")
    rows = await repo.get_with_join(Tag, Widget.id == Tag.id, join_on=Widget.id == Tag.id)
    assert isinstance(rows, list)
    assert await repo.update_where(criteria=[Widget.id == widget.id], values={"name": "ae"}) == 1
    assert (await repo.get(widget.id)).name == "ae"


@pytest.mark.asyncio
async def test_async_delete_all_and_mapping_helpers(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="async-sort")
    await repo.delete_all()
    await repo.create(name="async-sort")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    await repo.fetch_sorted_mappings(
        select(Widget.id, Widget.name),
        list_query=ListQuery(offset=0, limit=5),
        sort=sort,
    )
    await repo.fetch_mappings_page(select(Widget.id), limit=5, offset=0)
    await repo.fetch_statement_mappings(select(Widget.id))
    assert await repo.scalar_count(select(Widget.id)) >= 1
    async for _ in repo.iter_mappings(select(Widget.id)):
        break
    assert await repo.fetch_mapping_first(select(Widget.id)) is not None
    assert await repo.fetch_mapping_one(select(Widget.id))
    assert len(await repo.get_all(page=1, limit=1)) == 1
    assert len(await repo.filter(page=1, limit=1)) == 1


@pytest.mark.asyncio
async def test_async_update_partial_core_model(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Tag, async_session)
    created = await repo.create(label="x")
    assert (
        await repo.update_partial(
            created.id,
            {"label": "y"},
            frozenset({"label"}),
            touch_updated_on=False,
        )
        == 1
    )
    assert (await repo.get(created.id)).label == "y"
    assert await repo.update_partial(created.id, {"label": "z"}, frozenset()) == 0


@pytest.mark.asyncio
async def test_async_update_partial_rejects_unexpected_plan_action(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    created = await repo.create(name="guard")

    def bad_plan(*_args: object, **_kwargs: object) -> PartialUpdatePlan:
        return PartialUpdatePlan("invalid", {"name": "y"})  # type: ignore[arg-type]

    monkeypatch.setattr("sqlphilosophy.aio.repository.plan_partial_update", bad_plan)
    with pytest.raises(RuntimeError, match="unexpected partial update plan action"):
        await repo.update_partial(created.id, {"name": "y"}, frozenset({"name"}))


@pytest.mark.asyncio
async def test_async_update_partial_touch_updated_on(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(UpdatableTag, async_session)
    row = await repo.create(label="u")
    await repo.update_partial(row.id, {"label": "u2"}, frozenset({"label"}), touch_updated_on=True)
    await async_session.refresh(row)
    assert row.label == "u2"
    assert row.updated_on is not None


@pytest.mark.asyncio
async def test_async_batched_purge_no_matches_is_zero(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    assert await repo.batched_purge_ids(criteria=[Widget.name == "missing"], batch_size=5) == 0


@pytest.mark.asyncio
async def test_async_delete_many_empty_list_returns_zero(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    assert await repo.delete_many([]) == 0


@pytest.mark.asyncio
async def test_async_pagination_rejects_invalid_page_and_limit(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await repo.filter(page=1, limit=0)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await repo.get_all(limit=0)
    with pytest.raises(ValueError, match="page must be >= 1"):
        await repo.get_all(page=0)


@pytest.mark.asyncio
async def test_async_inspect_returns_mapper(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    assert repo.inspect() is not None


@pytest.mark.asyncio
async def test_async_repository_factory_creates_statements(async_session: AsyncSession) -> None:
    factory = _FakeAsyncFactory(async_session)
    repo = AsyncBaseRepository(Widget, async_session, factory)
    assert isinstance(repo.statement(), AsyncSqlAlchemyStatementBuilder)
    await repo.create(name="factory")
    first = await repo.first(name="factory")
    assert first is not None
    await repo.update_partial(first.id, {"name": "factory2"}, frozenset({"name"}))
    await repo.delete_where(criteria=[Widget.name == "factory2"], params={})
    assert await repo.batched_purge_ids(criteria=[Widget.name.like("factory%")], batch_size=1) == 0
