"""Async last-mile coverage."""

from __future__ import annotations
import pytest

from conftest import Child
from conftest import Parent
from conftest import Tag
from conftest import UpdatableTag
from conftest import Widget
from sqlalchemy import literal_column
from sqlalchemy import select
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery


@pytest.mark.asyncio
async def test_async_query_remaining(async_session) -> None:
    parent = Parent()
    async_session.add(parent)
    await async_session.flush()
    async_session.add(Child(parent_id=parent.id))
    await async_session.flush()
    b = AsyncSqlAlchemyStatementBuilder(async_session, Parent)
    b.select_table()
    b.select_columns(Parent.id)
    b.select_from(Parent)
    b.distinct(Parent.id)
    b.group_by(Parent.id)
    b.correlate(Parent)
    b.correlate_except(Child)
    b.as_lateral("p")
    b.as_cte("p")
    b.with_params({"x": 1})
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.limit(-1)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b.offset(-1)
    await b.count()
    await b.scalar()
    await b.mappings().all()
    await b.mappings().first()
    await b.mappings().one()
    await b.scalars().all()
    await b.scalars().first()
    b.build_select()


@pytest.mark.asyncio
async def test_async_query_filter_and_count(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="f")
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    b.filter_by(name="f")
    await b.count()
    empty = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    empty._stmt = select(literal_column("1"))
    await empty.count()
    await empty.scalar()
    await empty.count_distinct(Widget.id)
    await empty.fetch_page(ListQuery(offset=0, limit=0))
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await empty.fetch_page(ListQuery(offset=0, limit=-1))
    await (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .where(Widget.name == "f")
        .count_distinct(Widget.id)
    )
    empty.build_select()


@pytest.mark.asyncio
async def test_async_repository_remaining(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="left")
    await repo.create(name="delete-params")
    await repo.delete_where(criteria=[Widget.name == "delete-params"], params={"p": 1})
    await repo.get_with_join(Tag, Widget.id == Tag.id, join_on=Widget.id == Tag.id)
    assert await repo.update_partial(99999, {"name": "n"}, frozenset({"name"})) == 0
    assert await repo.update_partial(row.id, {"name": "n"}, frozenset()) == 0
    assert await repo.update_where(criteria=[Widget.id == row.id], values={}) == 0
    import uuid

    await repo.get_or_create(name=f"unique-{uuid.uuid4()}")
    upd_repo = AsyncBaseRepository(UpdatableTag, async_session)
    upd = await upd_repo.create(label="u")
    await upd_repo.update_partial(
        upd.id, {"label": "u2"}, frozenset({"label"}), touch_updated_on=True
    )
    with pytest.raises(ValueError, match="page must be >= 1"):
        await repo.filter(page=0)
    assert await repo.delete_many([]) == 0
    await repo.batched_purge_ids(criteria=[Widget.name == "missing"], batch_size=5)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await repo.get_all(limit=0)
    with pytest.raises(ValueError, match="page must be >= 1"):
        await repo.get_all(page=0)
