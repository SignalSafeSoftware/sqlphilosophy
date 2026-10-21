"""Readonly session identity permits safe service composition."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.repository import BaseRepository


class Base(DeclarativeBase):
    """Local test metadata."""


class Record(Base):
    __tablename__ = "session_record"
    id: Mapped[int] = mapped_column(primary_key=True)


def test_sync_repository_exposes_original_readonly_session() -> None:
    with Session() as session:
        repository = BaseRepository[Record, RepositoryFactory](Record, session)
        assert repository.session is session
        with pytest.raises(AttributeError):
            repository.session = None


@pytest.mark.asyncio
async def test_async_repository_exposes_original_readonly_session() -> None:
    async with AsyncSession() as session:
        repository = AsyncBaseRepository[Record, AsyncRepositoryFactory](Record, session)
        assert repository.session is session
        with pytest.raises(AttributeError):
            repository.session = None
