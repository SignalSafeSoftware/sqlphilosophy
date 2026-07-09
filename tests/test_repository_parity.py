"""Behavioral parity between sync and async repository implementations."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Tag, UpdatableTag, Widget
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.repository import BaseRepository


def test_sync_update_partial_audit_model_uses_orm_path(sync_session: Session) -> None:
    """Audit models load the row and apply writable fields via the ORM session."""
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="before")
    assert repo.update_partial(row.id, {"name": "after"}, frozenset({"name"})) == 1
    sync_session.refresh(row)
    assert row.name == "after"


@pytest.mark.asyncio
async def test_async_update_partial_audit_model_uses_orm_path(async_session: AsyncSession) -> None:
    """Async audit partial updates mirror sync: ORM load, setattr, flush, count 1."""
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="before")
    assert await repo.update_partial(row.id, {"name": "after"}, frozenset({"name"})) == 1
    await async_session.refresh(row)
    assert row.name == "after"


def test_sync_update_partial_missing_id_is_no_op(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    assert repo.update_partial(99999, {"name": "x"}, frozenset({"name"})) == 0


@pytest.mark.asyncio
async def test_async_update_partial_missing_id_is_no_op(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    assert await repo.update_partial(99999, {"name": "x"}, frozenset({"name"})) == 0


def test_sync_update_partial_empty_writable_is_no_op(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="keep")
    assert repo.update_partial(row.id, {"name": "drop"}, frozenset()) == 0
    sync_session.refresh(row)
    assert row.name == "keep"


@pytest.mark.asyncio
async def test_async_update_partial_empty_writable_is_no_op(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    row = await repo.create(name="keep")
    assert await repo.update_partial(row.id, {"name": "drop"}, frozenset()) == 0
    await async_session.refresh(row)
    assert row.name == "keep"


def test_sync_update_partial_core_touch_updated_on(sync_session: Session) -> None:
    repo = BaseRepository(UpdatableTag, sync_session)
    row = repo.create(label="core")
    assert (
        repo.update_partial(
            row.id,
            {"label": "touched"},
            frozenset({"label"}),
            touch_updated_on=True,
        )
        == 1
    )
    sync_session.refresh(row)
    assert row.label == "touched"
    assert row.updated_on is not None


@pytest.mark.asyncio
async def test_async_update_partial_core_touch_updated_on(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(UpdatableTag, async_session)
    row = await repo.create(label="core")
    assert (
        await repo.update_partial(
            row.id,
            {"label": "touched"},
            frozenset({"label"}),
            touch_updated_on=True,
        )
        == 1
    )
    await async_session.refresh(row)
    assert row.label == "touched"
    assert row.updated_on is not None


def test_sync_delete_where_empty_criteria_is_no_op(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="stay")
    assert repo.delete_where(criteria=[]) == 0
    assert repo.count() == 1


@pytest.mark.asyncio
async def test_async_delete_where_empty_criteria_is_no_op(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="stay")
    assert await repo.delete_where(criteria=[]) == 0
    assert await repo.count() == 1


def test_sync_delete_where_resolves_ids_then_deletes(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    keep = repo.create(name="keep")
    drop = repo.create(name="drop-me")
    deleted = repo.delete_where(criteria=[Widget.name == "drop-me"])
    assert deleted == 1
    assert repo.get_by_id(drop.id) is None
    assert repo.get_by_id(keep.id) is not None


@pytest.mark.asyncio
async def test_async_delete_where_resolves_ids_then_deletes(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    keep = await repo.create(name="keep")
    drop = await repo.create(name="drop-me")
    deleted = await repo.delete_where(criteria=[Widget.name == "drop-me"])
    assert deleted == 1
    assert await repo.get_by_id(drop.id) is None
    assert await repo.get_by_id(keep.id) is not None


def test_sync_batched_purge_ids_batches_and_commits(sync_session: Session, monkeypatch) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="purge-a")
    repo.create(name="purge-b")
    commits: list[None] = []
    monkeypatch.setattr(sync_session, "commit", lambda: commits.append(None))
    total = repo.batched_purge_ids(criteria=[Widget.name.like("purge-%")], batch_size=1)
    assert total == 2
    assert len(commits) == 2


@pytest.mark.asyncio
async def test_async_batched_purge_ids_batches_and_commits(async_session: AsyncSession, monkeypatch) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="purge-a")
    await repo.create(name="purge-b")
    commits: list[None] = []

    async def _record_commit() -> None:
        commits.append(None)

    monkeypatch.setattr(async_session, "commit", _record_commit)
    total = await repo.batched_purge_ids(criteria=[Widget.name.like("purge-%")], batch_size=1)
    assert total == 2
    assert len(commits) == 2


@pytest.mark.parametrize("batch_size", [0, -1])
def test_sync_batched_purge_ids_rejects_invalid_batch_size(sync_session: Session, batch_size: int) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        repo.batched_purge_ids(criteria=[Widget.name.like("x%")], batch_size=batch_size)


@pytest.mark.parametrize("batch_size", [0, -1])
@pytest.mark.asyncio
async def test_async_batched_purge_ids_rejects_invalid_batch_size(async_session: AsyncSession, batch_size: int) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        await repo.batched_purge_ids(criteria=[Widget.name.like("x%")], batch_size=batch_size)


@pytest.mark.parametrize(
    ("page", "limit", "message"),
    [
        (0, None, "page must be >= 1"),
        (1, 0, "limit must be >= 1"),
    ],
)
def test_sync_pagination_validation(page: int, limit: int | None, message: str, sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(ValueError, match=message):
        repo.filter(page=page, limit=limit)


@pytest.mark.parametrize(
    ("page", "limit", "message"),
    [
        (0, None, "page must be >= 1"),
        (1, 0, "limit must be >= 1"),
    ],
)
@pytest.mark.asyncio
async def test_async_pagination_validation(
    page: int, limit: int | None, message: str, async_session: AsyncSession
) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    with pytest.raises(ValueError, match=message):
        await repo.filter(page=page, limit=limit)


def test_sync_core_model_update_path(sync_session: Session) -> None:
    """Non-audit models use a core UPDATE statement for partial updates."""
    repo = BaseRepository(Tag, sync_session)
    row = repo.create(label="old")
    assert repo.update_partial(row.id, {"label": "new"}, frozenset({"label"})) == 1
    sync_session.expire(row)
    assert repo.get(row.id).label == "new"


@pytest.mark.asyncio
async def test_async_core_model_update_path(async_session: AsyncSession) -> None:
    repo = AsyncBaseRepository(Tag, async_session)
    row = await repo.create(label="old")
    assert await repo.update_partial(row.id, {"label": "new"}, frozenset({"label"})) == 1
    assert (await repo.get(row.id)).label == "new"
