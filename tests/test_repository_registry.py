"""Exact model lookup preserves explicit custom repositories and scope ownership."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Tag, Widget
from sqlphilosophy.aio.registry import AsyncRepositoryRegistry
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.registry import RepositoryRegistry
from sqlphilosophy.sync.repository import BaseRepository
from test_protocols import _FakeAsyncFactory, _FakeFactory


def test_sync_fallback_and_registered_lookup(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    registry = RepositoryRegistry()
    fallback = registry.repository(Widget, sync_session, factory)
    assert type(fallback) is BaseRepository
    assert fallback.model is Widget
    assert fallback.session is sync_session
    assert fallback.factory is factory

    class Custom(BaseRepository):
        pass

    registry.register(Widget, lambda session, owner: Custom(Widget, session, owner))
    first = registry.repository(Widget, sync_session, factory)
    assert isinstance(first, Custom)
    assert registry.repository(Widget, sync_session, factory) is not first
    assert type(registry.repository(Tag, sync_session, factory)) is BaseRepository
    with pytest.raises(ValueError, match="already"):
        registry.register(Widget, lambda session, owner: Custom(Widget, session, owner))
    with pytest.raises(TypeError, match="callable"):
        registry.register(Tag, None)


@pytest.mark.parametrize("mismatch", ["model", "session", "factory", "type"])
def test_sync_rejects_invalid_builder_results(sync_session: Session, mismatch: str) -> None:
    factory = _FakeFactory(sync_session)
    registry = RepositoryRegistry()
    with Session() as other:

        def build(session, owner):
            if mismatch == "type":
                return object()
            return BaseRepository(
                Tag if mismatch == "model" else Widget,
                other if mismatch == "session" else session,
                _FakeFactory(session) if mismatch == "factory" else owner,
            )

        registry.register(Widget, build)
        with pytest.raises((ValueError, TypeError), match="Repository"):
            registry.repository(Widget, sync_session, factory)


async def test_async_fallback_and_registered_lookup(async_session: AsyncSession) -> None:
    factory = _FakeAsyncFactory(async_session)
    registry = AsyncRepositoryRegistry()
    fallback = registry.repository(Widget, async_session, factory)
    assert type(fallback) is AsyncBaseRepository
    assert fallback.model is Widget
    assert fallback.session is async_session
    assert fallback.factory is factory

    class Custom(AsyncBaseRepository):
        pass

    registry.register(Widget, lambda session, owner: Custom(Widget, session, owner))
    first = registry.repository(Widget, async_session, factory)
    assert isinstance(first, Custom)
    assert registry.repository(Widget, async_session, factory) is not first
    assert type(registry.repository(Tag, async_session, factory)) is AsyncBaseRepository
    with pytest.raises(ValueError, match="already"):
        registry.register(Widget, lambda session, owner: Custom(Widget, session, owner))
    with pytest.raises(TypeError, match="callable"):
        registry.register(Tag, None)


@pytest.mark.parametrize("mismatch", ["model", "session", "factory", "type"])
async def test_async_rejects_invalid_builder_results(async_session: AsyncSession, mismatch: str) -> None:
    factory = _FakeAsyncFactory(async_session)
    registry = AsyncRepositoryRegistry()
    async with AsyncSession() as other:

        def build(session, owner):
            if mismatch == "type":
                return object()
            return AsyncBaseRepository(
                Tag if mismatch == "model" else Widget,
                other if mismatch == "session" else session,
                _FakeAsyncFactory(session) if mismatch == "factory" else owner,
            )

        registry.register(Widget, build)
        with pytest.raises((ValueError, TypeError), match="Repository"):
            registry.repository(Widget, async_session, factory)
