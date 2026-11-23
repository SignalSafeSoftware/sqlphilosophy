"""Repository projections compose scoped UNION snapshots in the caller's session."""

import pytest
from sqlalchemy import bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Tag, Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder, AsyncStatementQueryBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository


def sync_arm(session, model, column, name):
    return (
        SqlAlchemyStatementBuilder(session, model)
        .select_columns(model.id.label("id"), column.label("name"))
        .where(column == bindparam(name))
        .with_params({name: "visible"})
    )


def async_arm(session, model, column, name):
    return (
        AsyncSqlAlchemyStatementBuilder(session, model)
        .select_columns(model.id.label("id"), column.label("name"))
        .where(column == bindparam(name))
        .with_params({name: "visible"})
    )


def test_union_snapshots_keep_each_arm_scope_bindings_and_outer_paging(sync_session):
    for name in ("visible", "hidden"):
        BaseRepository(Widget, sync_session).create(name=name)
        BaseRepository(Tag, sync_session).create(label=name)
    first = sync_arm(sync_session, Widget, Widget.name, "widget_name")
    second = sync_arm(sync_session, Tag, Tag.label, "tag_name")
    composed = first.union_all(second)
    assert first.count() == second.count() == 1
    assert composed.count() == 2
    rows = composed.as_subquery("visible_content")
    selected = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(rows.c.id, rows.c.name)
        .select_from(rows)
        .where(rows.c.name == "visible")
        .order_by(rows.c.id)
    )
    assert selected.count() == 2
    assert len(selected.limit(1).offset(1).mappings().all()) == 1
    first.where(Widget.id < 0)
    second.where(Tag.id < 0)
    assert composed.count() == 2
    assert first.count() == second.count() == 0


@pytest.mark.asyncio
async def test_async_union_snapshots_keep_arm_scopes_bindings_and_outer_paging(async_session):
    for name in ("visible", "hidden"):
        await AsyncBaseRepository(Widget, async_session).create(name=name)
        await AsyncBaseRepository(Tag, async_session).create(label=name)
    first = async_arm(async_session, Widget, Widget.name, "widget_name")
    second = async_arm(async_session, Tag, Tag.label, "tag_name")
    composed = first.union_all(second)
    assert await first.count() == await second.count() == 1
    assert await composed.count() == 2
    rows = composed.as_subquery("visible_content")
    selected = (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(rows.c.id, rows.c.name)
        .select_from(rows)
        .where(rows.c.name == "visible")
        .order_by(rows.c.id)
    )
    assert await selected.count() == 2
    assert len(await selected.limit(1).offset(1).mappings().all()) == 1
    first.where(Widget.id < 0)
    second.where(Tag.id < 0)
    assert await composed.count() == 2
    assert await first.count() == await second.count() == 0


@pytest.mark.parametrize(
    ("builder", "session_class"),
    [
        (SqlAlchemyStatementBuilder, Session),
        (AsyncSqlAlchemyStatementBuilder, AsyncSession),
    ],
)
def test_union_rejects_missing_foreign_or_mismatched_selections(builder, session_class):
    session = session_class()
    first = builder(session, Widget).select_columns(Widget.id)
    with pytest.raises(ValueError, match="another selection"):
        first.union_all()
    for other in (object(), builder(session_class(), Widget)):
        with pytest.raises(ValueError, match="same session"):
            first.union_all(other)
    unmatched = builder(session, Widget)
    with pytest.raises(ValueError, match="number of columns"):
        first.union_all(unmatched)
    first.with_params({"name": "one"})
    second = builder(session, Widget).select_columns(Widget.id).with_params({"name": "two"})
    with pytest.raises(ValueError, match="conflicting bound"):
        first.union_all(second)
    second.with_params({"name": "one"})
    assert first.union_all(second).as_subquery().c.id is not None


@pytest.mark.parametrize("base", [StatementQueryBuilder, AsyncStatementQueryBuilder])
def test_new_composition_capabilities_do_not_break_existing_custom_builders(base):
    assert not {"as_subquery", "union_all"} & base.__abstractmethods__
    legacy = type(
        "LegacyBuilder",
        (base,),
        {name: lambda self, *args, **kwargs: None for name in base.__abstractmethods__},
    )()
    with pytest.raises(NotImplementedError):
        legacy.as_subquery()
    with pytest.raises(NotImplementedError):
        legacy.union_all(object())
