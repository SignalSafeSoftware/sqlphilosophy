"""Statement builder count() and fetch_page() total alignment."""

from __future__ import annotations

import pytest
from sqlalchemy import bindparam

from conftest import Child, Parent, Tag, Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def _seed_widgets(repo: BaseRepository[Widget]) -> None:
    repo.create(name="active-a", active=True)
    repo.create(name="active-b", active=True)
    repo.create(name="inactive", active=False)


async def _seed_widgets_async(repo: AsyncBaseRepository[Widget]) -> None:
    await repo.create(name="active-a", active=True)
    await repo.create(name="active-b", active=True)
    await repo.create(name="inactive", active=False)


def _seed_parent_child(sync_session) -> Parent:
    parent = Parent()
    sync_session.add(parent)
    sync_session.flush()
    sync_session.add_all([Child(parent_id=parent.id), Child(parent_id=parent.id)])
    sync_session.flush()
    return parent


async def _seed_parent_child_async(async_session) -> Parent:
    parent = Parent()
    async_session.add(parent)
    await async_session.flush()
    async_session.add_all([Child(parent_id=parent.id), Child(parent_id=parent.id)])
    await async_session.flush()
    return parent


def test_count_simple_filtered_query(sync_session) -> None:
    _seed_widgets(BaseRepository(Widget, sync_session))
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.active.is_(True))
    assert builder.count() == 2


def test_count_joined_query_returns_join_row_count(sync_session) -> None:
    _seed_parent_child(sync_session)
    builder = SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().join(Child)
    assert builder.count() == 2


def test_count_selected_columns_query(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="w1")
    BaseRepository(Tag, sync_session).create(label="t1")
    builder = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id, Tag.id)
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
    )
    assert builder.count() == 1


def test_portable_distinct_deduplicates_joined_rows(sync_session) -> None:
    _seed_parent_child(sync_session)
    builder = SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().join(Child).distinct()
    assert builder.count() == 1


def test_count_group_by_query_returns_group_count(sync_session) -> None:
    _seed_parent_child(sync_session)
    builder = SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().join(Child).group_by(Parent.id)
    assert builder.count() == 1


def test_count_ignores_limit_offset_and_order_by(sync_session) -> None:
    _seed_widgets(BaseRepository(Widget, sync_session))
    builder = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .order_by(Widget.name)
        .limit(1)
        .offset(1)
    )
    assert builder.count() == 2


def test_count_honors_with_params(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="needle")
    BaseRepository(Widget, sync_session).create(name="other")
    builder = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.name == bindparam("name"))
        .with_params({"name": "needle"})
    )
    assert builder.count() == 1


def test_fetch_page_total_matches_count_for_joined_query(sync_session) -> None:
    _seed_widgets(BaseRepository(Widget, sync_session))
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.active.is_(True))
    rows, total = builder.fetch_page(ListQuery(offset=0, limit=1), sort=sort)
    assert total == builder.count() == 2
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_async_count_simple_filtered_query(async_session) -> None:
    await _seed_widgets_async(AsyncBaseRepository(Widget, async_session))
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity().where(Widget.active.is_(True))
    assert await builder.count() == 2


@pytest.mark.asyncio
async def test_async_count_joined_query_returns_join_row_count(async_session) -> None:
    await _seed_parent_child_async(async_session)
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().join(Child)
    assert await builder.count() == 2


@pytest.mark.asyncio
async def test_async_count_selected_columns_query(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="w1")
    await AsyncBaseRepository(Tag, async_session).create(label="t1")
    builder = (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(Widget.id, Tag.id)
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
    )
    assert await builder.count() == 1


@pytest.mark.asyncio
async def test_async_portable_distinct_deduplicates_joined_rows(async_session) -> None:
    await _seed_parent_child_async(async_session)
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().join(Child).distinct()
    assert await builder.count() == 1


@pytest.mark.asyncio
async def test_async_count_group_by_query_returns_group_count(async_session) -> None:
    await _seed_parent_child_async(async_session)
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().join(Child).group_by(Parent.id)
    assert await builder.count() == 1


@pytest.mark.asyncio
async def test_async_count_ignores_limit_offset_and_order_by(async_session) -> None:
    await _seed_widgets_async(AsyncBaseRepository(Widget, async_session))
    builder = (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .order_by(Widget.name)
        .limit(1)
        .offset(1)
    )
    assert await builder.count() == 2


@pytest.mark.asyncio
async def test_async_count_honors_with_params(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="needle")
    await AsyncBaseRepository(Widget, async_session).create(name="other")
    builder = (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.name == bindparam("name"))
        .with_params({"name": "needle"})
    )
    assert await builder.count() == 1


@pytest.mark.asyncio
async def test_async_fetch_page_total_matches_count_for_joined_query(async_session) -> None:
    await _seed_widgets_async(AsyncBaseRepository(Widget, async_session))
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity().where(Widget.active.is_(True))
    rows, total = await builder.fetch_page(ListQuery(offset=0, limit=1), sort=sort)
    assert total == await builder.count() == 2
    assert len(rows) == 1
