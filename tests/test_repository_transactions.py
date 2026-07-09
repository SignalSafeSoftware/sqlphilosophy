"""Repository transaction ownership and destructive helper behavior."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from conftest import Base, Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_create_flushes_without_commit_until_caller_commits() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        repo = BaseRepository(Widget, session)
        row = repo.create(name="pending")
        row_id = row.id
        session.close()

        verify = sessionmaker(bind=engine)()
        try:
            assert verify.get(Widget, row_id) is None
        finally:
            verify.close()
    finally:
        engine.dispose()


def test_create_visible_after_explicit_commit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        repo = BaseRepository(Widget, session)
        row = repo.create(name="committed")
        row_id = row.id
        session.commit()
        session.close()

        verify = sessionmaker(bind=engine)()
        try:
            assert verify.get(Widget, row_id) is not None
        finally:
            verify.close()
    finally:
        engine.dispose()


def test_delete_all_does_not_commit(sync_session, monkeypatch) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="stay")
    sync_session.commit()

    commits: list[bool] = []
    original_commit = sync_session.commit

    def track_commit() -> None:
        commits.append(True)
        return original_commit()

    monkeypatch.setattr(sync_session, "commit", track_commit)
    deleted = repo.delete_all()
    assert deleted >= 1
    assert commits == []


def test_batched_purge_ids_commits_each_batch(sync_session, monkeypatch) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="purge-a")
    repo.create(name="purge-b")
    sync_session.commit()

    commits: list[bool] = []
    original_commit = sync_session.commit

    def track_commit() -> None:
        commits.append(True)
        return original_commit()

    monkeypatch.setattr(sync_session, "commit", track_commit)
    total = repo.batched_purge_ids(criteria=[Widget.name.like("purge-%")], batch_size=1)
    assert total == 2
    assert len(commits) >= 1


def test_apply_sort_rejects_disallowed_order_by_in_fetch_page(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="alpha")
    repo.create(name="beta")
    sync_session.commit()

    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    rows, total = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .apply_sort(sort, {"evil_column": "asc"})
        .fetch_page(ListQuery(offset=0, limit=10))
    )
    names = [row["name"] for row in rows]
    assert total == 2
    assert names == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_async_apply_sort_parity_with_sync() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as session:
        session.add(Widget(name="alpha"))
        session.add(Widget(name="beta"))
        await session.commit()

        sort = SortConfig(
            default=SortSpec("name", "asc"),
            columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
        )
        rows, total = await (
            AsyncSqlAlchemyStatementBuilder(session, Widget)
            .select_entity()
            .apply_sort(sort, {"name": "desc"})
            .fetch_page(ListQuery(offset=0, limit=10))
        )
        assert total == 2
        assert [row["name"] for row in rows] == ["beta", "alpha"]

    await engine.dispose()
