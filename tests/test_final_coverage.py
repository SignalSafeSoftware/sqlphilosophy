"""Final coverage for remaining sqlphilosophy lines."""

from __future__ import annotations
from datetime import datetime
from datetime import timezone
import pytest

from conftest import Child
from conftest import Parent
from conftest import Tag
from conftest import Widget
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.audit.listener import get_audit_listener
from sqlphilosophy.sql import delete_by_ids
from sqlphilosophy.sql import partial_update_model
from sqlphilosophy.sql import row_mapping
from sqlphilosophy.sql import row_opt_int
from sqlphilosophy.sql import row_opt_str
from sqlphilosophy.sql import select_page_from_table
from sqlphilosophy.sql import sql_table
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


class _Key:
    def __init__(self, key: str) -> None:
        self.key = key


def test_row_mapping_key_object_and_session_row(sync_session: Session) -> None:
    sync_session.add(Widget(name="rowmap"))
    sync_session.flush()
    result = sync_session.execute(select(Widget.id, Widget.name)).first()
    assert result is not None
    mapped = row_mapping(result)
    assert "name" in mapped
    assert row_mapping({_Key("id"): 1, "name": "x"})["id"] == 1


def test_row_opt_int_and_str_variants() -> None:
    assert row_opt_int({"n": 1.0}, "n") == 1
    assert row_opt_int({"n": "2"}, "n") == 2
    with pytest.raises(TypeError):
        row_opt_int({"n": object()}, "n")
    assert row_opt_str({"b": b"bytes"}, "b") == "bytes"
    with pytest.raises(TypeError):
        row_opt_str({"n": object()}, "n")


def test_delete_by_ids_empty() -> None:
    assert delete_by_ids(Session(), "widget", []) == 0


def test_select_page_without_where(sync_session: Session) -> None:
    w = Widget(name="page2")
    sync_session.add(w)
    sync_session.flush()
    tbl = sql_table("widget", "id", "name")
    rows = select_page_from_table(
        sync_session,
        tbl,
        [],
        {},
        order_by=Widget.id,  # type: ignore[arg-type]
        limit=5,
        offset=0,
    )
    assert rows


def test_sync_query_join_no_onclause_and_for_update(sync_session: Session) -> None:
    parent = Parent()
    sync_session.add(parent)
    sync_session.flush()
    sync_session.add(Child(parent_id=parent.id))
    sync_session.flush()
    SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().join(Child).count()
    SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().outerjoin(Child).count()
    SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().with_for_update(
        of=Parent
    ).count()
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id, Tag.id)
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
        .count()
    )


def test_sync_repository_remaining_branches(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    assert repo.update_where(criteria=[Widget.id == 999], values={}) == 0
    repo.create(name="params")
    assert repo.delete_where(criteria=[Widget.name == "params"], params={}) == 1
    with pytest.raises(ValueError, match="limit must be >= 1"):
        repo.get_all(limit=0)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        repo.filter(page=1, limit=0)


def test_audit_listener_nonempty_fields() -> None:
    listener = get_audit_listener()
    row = Widget(name="filled")
    row.created_on = datetime.now(timezone.utc)
    listener._set_if_empty(row, "created_on", datetime.now(timezone.utc))
    listener.stamp_on_update(row)


def test_partial_update_model_core_touch(sync_session: Session) -> None:
    tag = Tag(label="touch")
    sync_session.add(tag)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Tag,
            tag.id,
            {"label": "t2"},
            frozenset({"label"}),
            extra_values={"label": "t3"},
        )
        == 1
    )


@pytest.mark.asyncio
async def test_async_repository_factory_statement(async_session) -> None:
    class Factory(AsyncRepositoryFactory):
        def __init__(self, session) -> None:
            self._session = session

        @property
        def session(self):
            return self._session

        def create_statement(self, model):
            return AsyncSqlAlchemyStatementBuilder(self._session, model)

        def get_repository(self, repo_class):
            return repo_class(self._session, self)

    factory = Factory(async_session)
    repo = AsyncBaseRepository(Widget, async_session, factory)
    assert isinstance(repo.statement(), AsyncSqlAlchemyStatementBuilder)
    await repo.create(name="factory")
    await repo.update_partial(
        (await repo.first(name="factory")).id,  # type: ignore[union-attr]
        {"name": "factory2"},
        frozenset({"name"}),
    )
    await repo.delete_where(criteria=[Widget.name == "factory2"], params={})
    await repo.batched_purge_ids(criteria=[Widget.name.like("factory%")], batch_size=1)


@pytest.mark.asyncio
async def test_async_fetch_mappings_page_invalid(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        await repo.fetch_mappings_page(select(Widget.id), limit=-1, offset=0)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        await repo.fetch_mappings_page(select(Widget.id), limit=1, offset=-1)


@pytest.mark.asyncio
async def test_async_query_join_no_onclause(async_session) -> None:
    parent = Parent()
    async_session.add(parent)
    await async_session.flush()
    async_session.add(Child(parent_id=parent.id))
    await async_session.flush()
    await AsyncSqlAlchemyStatementBuilder(async_session, Parent).select_entity().join(Child).count()
    await (
        AsyncSqlAlchemyStatementBuilder(async_session, Parent)
        .select_entity()
        .outerjoin(Child)
        .count()
    )
    await (
        AsyncSqlAlchemyStatementBuilder(async_session, Parent)
        .select_entity()
        .with_for_update(of=Parent)
        .count()
    )
    await AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_table().distinct(
        Widget.id
    ).group_by(Widget.id).count()
