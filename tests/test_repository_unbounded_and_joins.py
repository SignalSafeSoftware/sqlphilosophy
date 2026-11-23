"""Unbounded reads, exhausted iterators and inferred joins preserve result semantics."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Child, Parent, Widget
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.audit.listener import get_audit_listener
from sqlphilosophy.audit.model import AuditMixin
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.repository import BaseRepository


def test_sync_unbounded_reads_keep_all_rows_in_primary_key_order(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    first = repo.create(name="first")
    second = repo.create(name="second")
    assert list(repo.get_all()) == [first, second]


async def test_async_unbounded_reads_keep_all_rows_in_primary_key_order(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    first = await repo.create(name="first")
    second = await repo.create(name="second")
    assert list(await repo.get_all()) == [first, second]


async def test_async_mapping_iterator_exhausts_and_keeps_order(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    first = await repo.create(name="first")
    second = await repo.create(name="second")
    statement = select(Widget.id, Widget.name).order_by(Widget.id)
    rows = [row async for row in repo.iter_mappings(statement)]
    assert rows == [{"id": first.id, "name": "first"}, {"id": second.id, "name": "second"}]


async def test_async_mappings_without_sort_preserve_statement_order_and_page(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    first = await repo.create(name="first")
    await repo.create(name="second")
    statement = select(Widget.id).order_by(Widget.id.desc())
    rows = await repo.fetch_sorted_mappings(statement, list_query=ListQuery(limit=1, offset=1))
    assert rows == [{"id": first.id}]


def test_sync_joins_infer_foreign_key_and_keep_all_matching_pairs(sync_session: Session) -> None:
    parents = BaseRepository(Parent, sync_session)
    children = BaseRepository(Child, sync_session)
    parent = parents.create()
    parents.create()
    first = children.create(parent_id=parent.id)
    second = children.create(parent_id=parent.id)
    rows = parents.get_with_join(Child)
    assert {(row.id, child.id) for row, child in rows} == {(parent.id, first.id), (parent.id, second.id)}


async def test_async_joins_infer_foreign_key_and_keep_all_matching_pairs(async_session: AsyncSession) -> None:
    parents = AsyncBaseRepository(Parent, async_session)
    children = AsyncBaseRepository(Child, async_session)
    parent = await parents.create()
    await parents.create()
    first = await children.create(parent_id=parent.id)
    second = await children.create(parent_id=parent.id)
    rows = await parents.get_with_join(Child)
    assert {(row.id, child.id) for row, child in rows} == {(parent.id, first.id), (parent.id, second.id)}


def test_update_stamping_does_not_add_columns_to_created_only_audit_models() -> None:
    class CreatedEvent(AuditMixin):
        created_on = datetime(2026, 1, 1, tzinfo=UTC)

    event = CreatedEvent()
    created = event.created_on
    get_audit_listener().stamp_on_update(event)
    assert event.created_on is created
    assert not hasattr(event, "updated_on")
