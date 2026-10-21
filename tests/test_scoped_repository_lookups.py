"""Real scoped query/rollback and subclass extension checks."""

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncStatementQueryBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository


class Base(DeclarativeBase):
    """Host-owned test metadata."""


class Record(Base):
    __tablename__ = "test_record"
    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String)
    order: Mapped[int] = mapped_column()


class TenantRepository(BaseRepository[Record, RepositoryFactory]):
    """A host overrides the query hook to add a stronger tenant scope."""

    def apply_scope(self, statement: StatementQueryBuilder[Record]) -> StatementQueryBuilder[Record]:
        return statement.where(Record.company == 1)


class AsyncTenantRepository(AsyncBaseRepository[Record, AsyncRepositoryFactory]):
    """Host async scope survives projection setup."""

    def apply_scope(self, statement: AsyncStatementQueryBuilder[Record]) -> AsyncStatementQueryBuilder[Record]:
        return statement.where(Record.company == 1)


def test_scopes_projection_rollback_and_repository_override() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = BaseRepository[Record, RepositoryFactory](Record, session)
        repo.add(Record(id=1, company=1, name="first", order=1))
        repo.add(Record(id=2, company=2, name="other", order=0))
        repo.add(Record(id=3, company=1, name="last", order=1))
        assert repo.find_entity(criteria=(Record.id == 1, Record.company == 2)) is None
        own = repo.find_entity(criteria=(Record.id == 1, Record.company == 1), lock=True)
        assert own is not None
        assert own.name == "first"
        assert repo.find_row(criteria=(Record.company == 2,), columns=(Record.name,)) == {"name": "other"}
        assert repo.count_scoped(criteria=(Record.company == 1,)) == 2
        with pytest.raises(ValueError, match="criteria"):
            repo.find_entity(criteria=())
        with pytest.raises(ValueError, match="projection"):
            repo.find_row(criteria=(Record.id == 1,), columns=())
        with pytest.raises(ValueError, match="criteria"):
            repo.count_scoped(criteria=())
        assert repo.find_row(criteria=(Record.id == 1,), columns=(Record.id,), lock=True) == {"id": 1}
        custom = TenantRepository(Record, session)
        assert custom.apply_scope(custom.statement()).count() == 2
        assert custom.find_entity(criteria=(Record.id == 2,)) is None
        assert custom.find_row(criteria=(Record.id == 2,), columns=(Record.name,)) is None
        assert custom.count_scoped(criteria=(Record.company == 2,)) == 0
        session.rollback()
        assert repo.statement().count() == 0
    engine.dispose()


@pytest.mark.asyncio
async def test_async_scope_and_caller_owned_transaction() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        repo = AsyncBaseRepository[Record, AsyncRepositoryFactory](Record, session)
        await repo.add(Record(id=1, company=1, name="owned", order=1))
        assert await repo.find_entity(criteria=(Record.company == 2,), lock=True) is None
        row = await repo.find_entity(criteria=(Record.company == 1,), lock=True)
        assert row is not None
        assert row.name == "owned"
        assert await repo.find_row(criteria=(Record.company == 1,), columns=(Record.name,), lock=True) == {
            "name": "owned"
        }
        assert await repo.count_scoped(criteria=(Record.company == 1,)) == 1
        with pytest.raises(ValueError, match="criteria"):
            await repo.find_entity(criteria=())
        with pytest.raises(ValueError, match="projection"):
            await repo.find_row(criteria=(Record.id == 1,), columns=())
        with pytest.raises(ValueError, match="criteria"):
            await repo.count_scoped(criteria=())
        await repo.add(Record(id=2, company=2, name="other", order=0))
        custom = AsyncTenantRepository(Record, session)
        assert await custom.find_entity(criteria=(Record.id == 2,)) is None
        assert await custom.find_row(criteria=(Record.id == 2,), columns=(Record.name,)) is None
        assert await custom.count_scoped(criteria=(Record.company == 2,)) == 0
        await session.rollback()
        assert await repo.statement().count() == 0
    await engine.dispose()
