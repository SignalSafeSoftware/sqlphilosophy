"""Static consumer regressions for SQLAlchemy 2.1's variadic Select rows."""

from collections.abc import Sequence
from typing import assert_type

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.types import SqlSelect


class Model(DeclarativeBase):
    __tablename__ = "typing_model"
    id: Mapped[int] = mapped_column(primary_key=True)


def sync_contract(repository: BaseRepository[Model, RepositoryFactory]) -> None:
    assert_type(repository.get_by_id(1), Model | None)
    assert_type(repository.get_many([1]), Sequence[Model])
    statement = repository.statement().build_select()
    assert_type(statement, SqlSelect)


async def async_contract(repository: AsyncBaseRepository[Model, AsyncRepositoryFactory]) -> None:
    assert_type(await repository.get_by_id(1), Model | None)
    assert_type(await repository.get_many([1]), Sequence[Model])
    statement = repository.statement().build_select()
    assert_type(statement, SqlSelect)
