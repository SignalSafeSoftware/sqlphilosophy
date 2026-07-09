"""Statement builder scalar() and scalar_one() behavior."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from conftest import Widget
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_scalar_returns_value_for_one_row(sync_session) -> None:
    row = BaseRepository(Widget, sync_session).create(name="only")
    value = (
        SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).where(Widget.id == row.id).scalar()
    )
    assert value == row.id


def test_scalar_returns_none_for_no_rows(sync_session) -> None:
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).where(Widget.id == 99999).scalar()
        is None
    )


def test_scalar_raises_for_multiple_rows(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="a")
    repo.create(name="b")
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id)
    with pytest.raises(MultipleResultsFound):
        builder.scalar()


def test_scalar_one_returns_value_for_one_row(sync_session) -> None:
    row = BaseRepository(Widget, sync_session).create(name="only")
    value = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id)
        .where(Widget.id == row.id)
        .scalar_one()
    )
    assert value == row.id


def test_scalar_one_raises_for_no_rows(sync_session) -> None:
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).where(Widget.id == 99999)
    with pytest.raises(NoResultFound):
        builder.scalar_one()


def test_scalar_one_raises_for_multiple_rows(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="a")
    repo.create(name="b")
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id)
    with pytest.raises(MultipleResultsFound):
        builder.scalar_one()


@pytest.mark.asyncio
async def test_async_scalar_returns_value_for_one_row(async_session) -> None:
    row = await AsyncBaseRepository(Widget, async_session).create(name="only")
    value = await (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(Widget.id)
        .where(Widget.id == row.id)
        .scalar()
    )
    assert value == row.id


@pytest.mark.asyncio
async def test_async_scalar_returns_none_for_no_rows(async_session) -> None:
    assert (
        await AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(Widget.id)
        .where(Widget.id == 99999)
        .scalar()
        is None
    )


@pytest.mark.asyncio
async def test_async_scalar_raises_for_multiple_rows(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="a")
    await repo.create(name="b")
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_columns(Widget.id)
    with pytest.raises(MultipleResultsFound):
        await builder.scalar()


@pytest.mark.asyncio
async def test_async_scalar_one_returns_value_for_one_row(async_session) -> None:
    row = await AsyncBaseRepository(Widget, async_session).create(name="only")
    value = await (
        AsyncSqlAlchemyStatementBuilder(async_session, Widget)
        .select_columns(Widget.id)
        .where(Widget.id == row.id)
        .scalar_one()
    )
    assert value == row.id


@pytest.mark.asyncio
async def test_async_scalar_one_raises_for_no_rows(async_session) -> None:
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_columns(Widget.id).where(Widget.id == 99999)
    with pytest.raises(NoResultFound):
        await builder.scalar_one()


@pytest.mark.asyncio
async def test_async_scalar_one_raises_for_multiple_rows(async_session) -> None:
    repo = AsyncBaseRepository(Widget, async_session)
    await repo.create(name="a")
    await repo.create(name="b")
    builder = AsyncSqlAlchemyStatementBuilder(async_session, Widget).select_columns(Widget.id)
    with pytest.raises(MultipleResultsFound):
        await builder.scalar_one()
