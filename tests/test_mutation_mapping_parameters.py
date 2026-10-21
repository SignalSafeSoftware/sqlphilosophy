"""Bulk mutation parameters obey the public Mapping protocol in both runtimes."""

from types import MappingProxyType

from sqlalchemy import bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from conftest import Widget
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.types import RowMapping


def test_sync_mutations_accept_immutable_parameters(sync_session: Session) -> None:
    repository = BaseRepository(Widget, sync_session)
    widget = repository.create(name="before", active=True)
    parameters: RowMapping = MappingProxyType({"chosen_id": widget.id})
    assert repository.update_where(
        criteria=[Widget.id == bindparam("chosen_id")],
        values={"name": "after"},
        params=parameters,
    ) == 1
    assert parameters == {"chosen_id": widget.id}
    assert repository.delete_where(
        criteria=[Widget.id == bindparam("chosen_id")], params=parameters
    ) == 1
    assert parameters == {"chosen_id": widget.id}


async def test_async_mutations_accept_immutable_parameters(async_session: AsyncSession) -> None:
    repository = AsyncBaseRepository(Widget, async_session)
    widget = await repository.create(name="before", active=True)
    parameters: RowMapping = MappingProxyType({"chosen_id": widget.id})
    assert await repository.update_where(
        criteria=[Widget.id == bindparam("chosen_id")],
        values={"name": "after"},
        params=parameters,
    ) == 1
    assert parameters == {"chosen_id": widget.id}
    assert await repository.delete_where(
        criteria=[Widget.id == bindparam("chosen_id")], params=parameters
    ) == 1
    assert parameters == {"chosen_id": widget.id}
