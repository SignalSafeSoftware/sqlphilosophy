"""Async AsyncSqlAlchemyStatementBuilder behavior."""

from __future__ import annotations

import pytest
from sqlalchemy import literal_column, select
from sqlalchemy.dialects import postgresql

from conftest import Child, Parent, Tag, Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec


@pytest.mark.asyncio
async def test_async_query_builder(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="z")
    await repo.create(name="a")
    builder = (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .order_by(Widget.name)
        .limit(10)
        .offset(0)
    )
    scalars = await builder.scalars().all()
    assert len(scalars) == 2
    assert await builder.scalars().first() is not None
    assert await builder.select_columns(Widget.id).limit(1).scalar() is not None
    mappings = await builder.select_entity().mappings().all()
    assert mappings
    assert await builder.count() == 2
    assert await builder.count_distinct(Widget.id) == 2


@pytest.mark.asyncio
async def test_async_mappings_terminals(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="m")
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_columns(Widget.id, Widget.name)
    assert await b.mappings().all()
    assert await b.mappings().first() is not None
    assert (await b.mappings().one())["name"] == "m"


@pytest.mark.asyncio
async def test_async_fetch_page(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    for i in range(4):
        await repo.create(name=f"n{i}")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    rows, total = await (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(Widget.id, Widget.name)
        .fetch_page(ListQuery(offset=0, limit=2), sort=sort)
    )
    assert total == 4
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_async_fetch_page_does_not_mutate_builder(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    for i in range(5):
        await repo.create(name=f"n{i}")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity().where(Widget.active.is_(True))
    rows, total = await builder.fetch_page(ListQuery(offset=0, limit=2), sort=sort)
    assert total == 5
    assert len(rows) == 2
    assert len(await builder.scalars().all()) == 5
    assert await builder.count() == 5


@pytest.mark.asyncio
async def test_async_limit_offset_still_mutates_builder(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    for i in range(4):
        await repo.create(name=f"n{i}")
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity().order_by(Widget.id)
    builder.limit(2).offset(1)
    assert len(await builder.scalars().all()) == 2


@pytest.mark.asyncio
async def test_async_limit_offset_validation(async_session) -> None:
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.limit(-1)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b.offset(-1)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await b.fetch_page(ListQuery(offset=0, limit=-1), sort=None)


@pytest.mark.asyncio
async def test_async_count_with_implicit_join_onclause(async_session) -> None:
    parent = Parent()
    async_session.add(parent)
    await async_session.flush()
    async_session.add(Child(parent_id=parent.id))
    await async_session.flush()
    assert await AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().join(Child).count() >= 1
    assert await AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().outerjoin(Child).count() >= 1


@pytest.mark.asyncio
async def test_async_count_with_for_update_and_distinct_group_by(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="lock")
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity().with_for_update(of=Widget).count()
        == 1
    )
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_table()
        .distinct()
        .group_by(Widget.id)
        .count()
        >= 1
    )


@pytest.mark.asyncio
async def test_async_builder_table_select_and_correlate(async_session) -> None:
    parent = Parent()
    async_session.add(parent)
    await async_session.flush()
    async_session.add(Child(parent_id=parent.id))
    await async_session.flush()
    b = AsyncSqlAlchemyStatementBuilder(async_session, Parent)
    b.select_table()
    b.select_columns(Parent.id)
    b.select_from(Parent)
    b.distinct()
    b.group_by(Parent.id)
    b.correlate(Parent)
    b.correlate_except(Child)
    b.as_lateral("p")
    b.as_cte("p")
    b.with_params({"x": 1})
    assert await b.count() >= 1
    assert await b.scalar() is not None
    assert await b.mappings().all()
    assert await b.mappings().first() is not None
    assert await b.mappings().one()
    assert await b.scalars().all()
    assert await b.scalars().first() is not None
    assert b.build_select() is not None


@pytest.mark.asyncio
async def test_async_distinct_columns_compile_postgresql_distinct_on(async_session) -> None:
    stmt = AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().distinct(Parent.id).build_select()
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "DISTINCT ON (parent.id)" in compiled


@pytest.mark.asyncio
async def test_async_count_on_literal_select_and_zero_limit_page(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="f")
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    b.filter_by(name="f")
    assert await b.count() == 1
    empty = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    empty._stmt = select(literal_column("1"))
    assert await empty.count() == 1
    assert await empty.scalar() == 1
    assert await empty.count_distinct(Widget.id) >= 0
    rows, total = await empty.fetch_page(ListQuery(offset=0, limit=0))
    assert rows == []
    assert total == 1
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await empty.fetch_page(ListQuery(offset=0, limit=-1))
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.name == "f")
        .count_distinct(Widget.id)
        == 1
    )
    empty.build_select()


@pytest.mark.asyncio
async def test_async_query_builder_extended_join_and_correlate(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="aq1")
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    b.select_table().join(Tag, Widget.id == Tag.id)
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .outerjoin(Tag, Widget.id == Tag.id)
        .correlate(Widget)
        .correlate_except(Tag)
        .with_for_update(skip_locked=True)
        .count()
        >= 0
    )
    b2 = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity()
    _, total = await b2.fetch_page(ListQuery(offset=0, limit=1))
    assert total >= 1
    assert await b2.count_distinct(Widget.id) >= 1
    with pytest.raises(ValueError, match="offset must be >= 0"):
        await b2.fetch_page(ListQuery(offset=-1, limit=1))


@pytest.mark.asyncio
async def test_async_count_distinct_applies_existing_where_clause(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="distinct-a")
    await AsyncBaseRepository(Widget, async_session).create(name="distinct-b")
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.name == "distinct-a")
        .count_distinct(Widget.id)
        == 1
    )
