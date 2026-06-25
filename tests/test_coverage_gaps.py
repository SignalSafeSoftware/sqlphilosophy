"""Additional tests for full sqlphilosophy coverage."""

from __future__ import annotations
from datetime import date
from datetime import datetime
from uuid import uuid4
import pytest

from conftest import Tag
from conftest import Widget
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.audit.listener import get_audit_listener
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec
from sqlphilosophy.sql import apply_writable_update
from sqlphilosophy.sql import order_by_allowlist
from sqlphilosophy.sql import partial_update
from sqlphilosophy.sql import partial_update_model
from sqlphilosophy.sql import row_float
from sqlphilosophy.sql import row_int
from sqlphilosophy.sql import row_json
from sqlphilosophy.sql import row_mapping
from sqlphilosophy.sql import row_opt_bool
from sqlphilosophy.sql import row_opt_float
from sqlphilosophy.sql import row_opt_int
from sqlphilosophy.sql import row_opt_json_object
from sqlphilosophy.sql import row_opt_str
from sqlphilosophy.sql import row_opt_uuid
from sqlphilosophy.sql import row_str
from sqlphilosophy.sql import row_uuid
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_row_type_error_branches() -> None:
    with pytest.raises((TypeError, ValueError)):
        row_int({"x": "bad"}, "x")
    with pytest.raises(TypeError):
        row_int({"x": object()}, "x")
    with pytest.raises(TypeError):
        row_opt_int({"x": True}, "x")
    with pytest.raises(TypeError):
        row_str({"x": object()}, "x")
    with pytest.raises(TypeError):
        row_opt_str({"x": object()}, "x")
    with pytest.raises(TypeError):
        row_opt_bool({"x": 1}, "x")
    with pytest.raises(TypeError):
        row_float({"x": True}, "x")
    with pytest.raises(TypeError):
        row_opt_float({"x": True}, "x")
    with pytest.raises(TypeError):
        row_uuid({"x": 1}, "x")
    with pytest.raises((TypeError, ValueError)):
        row_opt_uuid({"x": 1}, "x")
    with pytest.raises(TypeError):
        row_json({"x": datetime.now()}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": []}, "x")


def test_row_coercion_success_variants() -> None:
    uid = uuid4()
    row = {
        "i": 2.0,
        "s": 1,
        "b": False,
        "f": 3,
        "uid": str(uid),
        "d": date.today(),
    }
    assert row_int(row, "i") == 2
    assert row_str(row, "s") == "1"
    assert row_opt_int(row, "missing") is None
    assert row_opt_str(row, "missing") is None
    assert row_opt_bool(row, "b") is False
    assert row_opt_float(row, "f") == pytest.approx(3.0)
    assert row_uuid(row, "uid") == uid


def test_partial_update_model_core_non_audit(sync_session: Session) -> None:
    tag = Tag(label="core")
    sync_session.add(tag)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Tag,
            tag.id,
            {"label": "updated"},
            frozenset({"label"}),
            touch_updated_on=False,
        )
        == 1
    )


def test_sync_repository_remaining(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    w = repo.create(name="remain")
    from sqlalchemy.orm import Load

    stmt = select(Widget).where(Widget.id == w.id)
    repo._apply_load_relations(stmt, [Load(Widget)])
    repo.fetch_sorted_mappings(
        select(Widget.id),
        list_query=ListQuery(offset=0, limit=5),
        sort=None,
    )
    repo.get_many([w.id], load_relations=[Load(Widget)])
    repo.delete_where(criteria=[Widget.id == w.id], params={})
    repo.get_with_join(Tag, Widget.id == Tag.id, join_on=Widget.id == Tag.id)


def test_apply_mappings_page_invalid_offset(sync_session: Session) -> None:
    from sqlphilosophy.sql import apply_mappings_page

    with pytest.raises(ValueError, match="offset must be >= 0"):
        apply_mappings_page(sync_session, select(Widget.id), limit=1, offset=-1)


def test_col_range_lte_and_merge_none() -> None:
    from sqlphilosophy.sql import col_range
    from sqlphilosophy.sql import merge_criteria

    crit, params = col_range("t.id", "hi", "<=", 9)
    assert params["hi"] == 9
    criteria, _ = merge_criteria(None, ([crit], params))
    assert criteria


def test_count_from_table_no_criteria(sync_session: Session) -> None:
    from sqlphilosophy.sql import count_from_table
    from sqlphilosophy.sql import sql_table

    Widget(name="c").id  # noqa: B018
    w = Widget(name="c")
    sync_session.add(w)
    sync_session.flush()
    tbl = sql_table("widget", "id", "name")
    assert count_from_table(sync_session, tbl, [], {}) >= 1


def test_api_int_float_more_branches() -> None:
    from sqlphilosophy.sql import api_float
    from sqlphilosophy.sql import api_int

    assert api_int({"x": 1.5}, "x") == 1
    assert api_int({"x": "3"}, "x") == 3
    assert api_float({"x": True}, "x") == pytest.approx(1.0)
    assert api_float({"x": "2.5"}, "x") == pytest.approx(2.5)
    assert api_float({"x": object()}, "x") == pytest.approx(0.0)


def test_partial_update_model_branches(sync_session: Session) -> None:
    row = Widget(name="touch")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Widget,
            row.id,
            {"name": "touched"},
            frozenset({"name"}),
            touch_updated_on=True,
            extra_values={"active": False},
        )
        == 1
    )
    assert partial_update_model(sync_session, Widget, 9999, {"name": "x"}, frozenset({"name"})) == 0
    assert partial_update_model(sync_session, Widget, row.id, {"name": "x"}, frozenset()) == 0


def test_partial_update_touch_and_extra(sync_session: Session) -> None:
    row = Widget(name="core")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update(
            sync_session,
            "widget",
            row.id,
            {"name": "core2"},
            frozenset({"name"}),
            touch_updated_on=True,
            extra_values={"active": False},
        )
        == 1
    )


def test_apply_writable_update(sync_session: Session) -> None:
    row = Widget(name="writable")
    sync_session.add(row)
    sync_session.flush()
    apply_writable_update(sync_session, Widget, row.id, {"name": "w2"}, frozenset({"name"}))
    apply_writable_update(sync_session, Widget, row.id, {"name": "ignored"}, frozenset())


def test_order_by_allowlist_invalid() -> None:
    with pytest.raises(ValueError, match="invalid order key"):
        order_by_allowlist("bad", {"name": "n ASC"}, allowlist=frozenset({"name"}))


def test_sync_repository_extended(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    w = repo.create(name="join")
    BaseRepository(Tag, sync_session).create(label="lbl")
    rows = repo.get_with_join(Tag, join_on=Widget.id == Tag.id)
    assert isinstance(rows, list)
    assert repo.update_where(criteria=[Widget.id == w.id], values={"name": "updated"}) == 1
    assert repo.delete_where(criteria=[]) == 0
    assert repo.delete_all() >= 0
    repo.create(name="sorted")
    from sqlalchemy import select as sa_select

    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    repo.fetch_sorted_mappings(
        sa_select(Widget.id, Widget.name),
        list_query=ListQuery(offset=0, limit=5),
        sort=sort,
    )
    repo.fetch_mappings_page(sa_select(Widget.id), limit=5, offset=0)


def test_sync_repository_load_relations_and_filter(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    for i in range(3):
        repo.create(name=f"p{i}")
    loaded = repo.filter(page=2, limit=1)
    assert len(loaded) == 1
    repo.get_all(page=1, limit=2)


def test_sync_query_extended(sync_session: Session) -> None:
    BaseRepository(Widget, sync_session).create(name="q1")
    BaseRepository(Widget, sync_session).create(name="q2")
    b = SqlAlchemyStatementBuilder(sync_session, Widget)
    b.select_table().join(Tag, Widget.id == Tag.id)
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .outerjoin(Tag, Widget.id == Tag.id)
        .correlate(Widget)
        .correlate_except(Tag)
        .with_for_update(skip_locked=True)
        .count()
    )
    b2 = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.name.isnot(None))
    )
    rows, total = b2.fetch_page(ListQuery(offset=0, limit=1))
    assert total >= 1
    assert len(rows) == 1
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b2.fetch_page(ListQuery(offset=-1, limit=1))


def test_row_mapping_orm_instance(sync_session: Session) -> None:
    row = Widget(name="orm")
    sync_session.add(row)
    sync_session.flush()
    mapped = row_mapping(row)
    assert mapped["name"] == "orm"


def test_audit_listener_update_without_actor(sync_session: Session) -> None:
    listener = get_audit_listener()
    row = Widget(name="no-actor")
    sync_session.add(row)
    sync_session.flush()
    listener.stamp_on_update(row)
    listener.stamp_on_soft_delete(row, actor=None)


@pytest.mark.asyncio
async def test_async_repository_extended(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    w = await repo.create(name="async-ext")
    await AsyncBaseRepository(Tag, async_session).create(label="t")
    rows = await repo.get_with_join(Tag, join_on=Widget.id == Tag.id)
    assert isinstance(rows, list)
    assert await repo.update_where(criteria=[Widget.id == w.id], values={"name": "ae"}) == 1
    assert await repo.delete_where(criteria=[]) == 0
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
    await repo.scalar_count(select(Widget.id))
    async for _ in repo.iter_mappings(select(Widget.id)):
        break
    await repo.fetch_mapping_first(select(Widget.id))
    await repo.fetch_mapping_one(select(Widget.id))
    await repo.get_all(page=1, limit=1)
    await repo.filter(page=1, limit=1)
    await repo.batched_purge_ids(criteria=[Widget.name.like("async%")], batch_size=10)


@pytest.mark.asyncio
async def test_async_query_extended(async_session) -> None:
    await AsyncBaseRepository(Widget, async_session).create(name="aq1")
    b = AsyncSqlAlchemyStatementBuilder(async_session, Widget)
    b.select_table().join(Tag, Widget.id == Tag.id)
    await (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_entity()
        .outerjoin(Tag, Widget.id == Tag.id)
        .correlate(Widget)
        .correlate_except(Tag)
        .with_for_update(skip_locked=True)
        .count()
    )
    b2 = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_entity()
    _, total = await b2.fetch_page(ListQuery(offset=0, limit=1))
    assert total >= 1
    await b2.count_distinct(Widget.id)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        await b2.fetch_page(ListQuery(offset=-1, limit=1))


@pytest.mark.asyncio
async def test_async_update_partial_core_path(async_session) -> None:
    repo = AsyncBaseRepository(Tag, async_session)
    created = await repo.create(label="x")
    updated = await repo.update_partial(
        created.id,
        {"label": "y"},
        frozenset({"label"}),
        touch_updated_on=False,
    )
    assert updated == 1
    assert await repo.update_partial(created.id, {"label": "z"}, frozenset()) == 0
