"""Sync BaseRepository behavior."""

from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from conftest import Widget
from conftest import WidgetTag
from sqlalchemy.orm import Session
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


class _FakeFactory(RepositoryFactory):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.created: list[type] = []

    @property
    def session(self) -> Session:
        return self._session

    def create_statement(self, model: type) -> SqlAlchemyStatementBuilder:
        self.created.append(model)
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type):
        return repo_class(self._session, self)


class _OtherRepo(BaseRepository[Widget, RepositoryFactory]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(Widget, session, factory)


def test_create_add_get(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    created = repo.create(name="alpha")
    assert created.id is not None
    assert repo.get_by_id(created.id) is created
    assert repo.get(created.id).name == "alpha"


def test_get_many_filter_count(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    a = repo.create(name="a", active=True)
    b = repo.create(name="b", active=False)
    assert len(repo.get_many([a.id, b.id])) == 2
    assert repo.get_many([]) == []
    assert repo.count(active=True) == 1
    assert len(repo.filter(active=True)) == 1


def test_remove_delete_many(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="gone")
    assert repo.remove(row.id) is True
    assert repo.get_by_id(row.id) is None
    one = repo.create(name="x")
    two = repo.create(name="y")
    assert repo.delete_many([one.id, two.id]) == 2


def test_statement_without_factory(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    builder = repo.statement()
    assert isinstance(builder, SqlAlchemyStatementBuilder)


def test_for_repo_without_factory_raises(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(RuntimeError, match="RepositoryFactory"):
        repo.for_repo(_OtherRepo)


def test_for_repo_with_factory(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    other = repo.for_repo(_OtherRepo)
    assert isinstance(other, _OtherRepo)


def test_composite_primary_key_rejected() -> None:
    with pytest.raises(TypeError, match="single-column primary key"):
        BaseRepository(WidgetTag, MagicMock())


def test_get_raises_lookup(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(LookupError):
        repo.get(9999)


def test_pagination_validation(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(ValueError, match="page must be >= 1"):
        repo.filter(page=0)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        repo.get_all(limit=0)


def test_get_or_create(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    obj, created = repo.get_or_create(name="new")
    assert created is True
    again, created2 = repo.get_or_create(name="new")
    assert created2 is False
    assert again.id == obj.id


def test_update_partial_and_delete_where(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="old")
    updated = repo.update_partial(row.id, {"name": "new"}, frozenset({"name"}))
    assert updated == 1
    sync_session.refresh(row)
    assert row.name == "new"
    repo.create(name="purge")
    deleted = repo.delete_where(criteria=[Widget.name == "purge"])
    assert deleted == 1


def test_batched_purge_ids(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="b1")
    repo.create(name="b2")
    total = repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=1)
    assert total == 2


def test_fetch_helpers(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="mapped")
    from sqlalchemy import select

    stmt = select(Widget.id, Widget.name)
    rows = repo.fetch_statement_mappings(stmt)
    assert rows
    assert repo.scalar_count(select(Widget.id)) >= 1
    assert list(repo.iter_mappings(stmt))
    assert repo.fetch_mapping_first(stmt) is not None
    assert repo.fetch_mapping_one(stmt.select_from(Widget).where(Widget.id == rows[0]["id"]))


def test_exists_helpers(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="exists")
    assert repo.exists(row.id)
    assert repo.exists_where(name="exists")


def test_schema_helpers(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    assert repo.inspect() is BaseRepository.inspect_model(Widget)
    names = repo.list_table_names()
    assert "widget" in names
    assert repo.has_table("widget")
    assert repo.has_table("missing") is False
