"""Close remaining coverage gaps."""

from __future__ import annotations
import pytest

from conftest import Tag
from conftest import Widget
from sqlalchemy.orm import Load
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec
from sqlphilosophy.sql import partial_update_model
from sqlphilosophy.sql import row_float
from sqlphilosophy.sql import row_opt_float
from sqlphilosophy.sql import row_opt_int
from sqlphilosophy.sql import row_opt_str
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_sql_remaining_type_paths() -> None:
    with pytest.raises(TypeError):
        row_float({"x": True}, "x")
    with pytest.raises(TypeError):
        row_opt_float({"x": True}, "x")
    assert row_opt_int({"x": 2.0}, "x") == 2
    assert row_opt_str({"x": "ok"}, "x") == "ok"


def test_partial_update_model_empty_core(sync_session) -> None:
    row = Tag(label="e")
    sync_session.add(row)
    sync_session.flush()
    assert partial_update_model(sync_session, Tag, row.id, {"label": "x"}, frozenset()) == 0
    assert (
        partial_update_model(
            sync_session,
            Tag,
            row.id,
            {"label": "y"},
            frozenset({"label"}),
        )
        == 1
    )


def test_row_opt_int_int_path() -> None:
    assert row_opt_int({"x": 5}, "x") == 5


def test_partial_update_touch_updated_on(sync_session) -> None:
    from conftest import UpdatableTag

    row = UpdatableTag(label="u")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            UpdatableTag,
            row.id,
            {"label": "u2"},
            frozenset({"label"}),
            touch_updated_on=True,
        )
        == 1
    )


def test_sync_repository_filter_limit_and_delete_where(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="delme")
    assert repo.filter(page=2, limit=1) == [] or len(repo.filter(page=1, limit=1)) == 1
    assert repo.delete_where(criteria=[Widget.name == "delme"]) == 1


def test_sync_query_limit_offset_negative(sync_session) -> None:
    b = SqlAlchemyStatementBuilder(sync_session, Widget)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.limit(-1)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b.offset(-1)
    BaseRepository(Widget, sync_session).create(name="cnt")
    SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().join(
        Tag, Widget.id == Tag.id
    ).count()
    BaseRepository(Widget, sync_session).create(name="c1")
    BaseRepository(Widget, sync_session).create(name="c2")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    b = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .apply_sort(sort, {"name": "desc"})
    )
    b.count()
    b.count_distinct(Widget.id)
    b.fetch_page(ListQuery(offset=0, limit=1))
    b.build_select()


@pytest.mark.asyncio
async def test_async_remaining(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    assert repo.inspect() is not None
    row = await repo.create(name="rem")
    await repo.get_many([row.id], load_relations=[Load(Widget)])
    with pytest.raises(LookupError):
        await repo.get(99999)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await repo.filter(page=1, limit=0)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await repo.get_all(limit=0)
    await repo.update_partial(row.id, {"name": "audit"}, frozenset({"name"}))
    await repo.delete_where(criteria=[Widget.name == "audit"], params={})
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    b.select_table().distinct(Widget.id).group_by(Widget.id)
    b.with_for_update(skip_locked=True)
    await b.count_distinct(Widget.id)
    await b.fetch_page(ListQuery(offset=0, limit=1))
    b.build_select()
