"""Async AsyncSqlAlchemyStatementBuilder behavior."""

from __future__ import annotations
import pytest

from conftest import Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec


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
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_columns(
        Widget.id, Widget.name
    )
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
async def test_async_limit_offset_validation(async_session) -> None:
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.limit(-1)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b.offset(-1)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await b.fetch_page(ListQuery(offset=0, limit=-1), sort=None)
