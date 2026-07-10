"""Sync BaseRepository behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from servicephilosophy.exceptions import FactoryRequiredError
from sqlalchemy import select
from sqlalchemy.orm import Load, Session

from conftest import Tag, Widget, WidgetTag
from sqlphilosophy.sorting import ListQuery
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

    def repository(self, model: type):
        return BaseRepository(model, self._session, self)


class _OtherRepo(BaseRepository[Widget, RepositoryFactory]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(Widget, session, factory)


# --- servicephilosophy factory exposure (sync) ---


def test_sync_has_factory_true_when_factory_configured(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    assert repo.has_factory is True


def test_sync_maybe_factory_returns_factory_when_configured(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    assert repo.maybe_factory is factory


def test_sync_factory_returns_factory_when_configured(sync_session: Session) -> None:
    factory = _FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    assert repo.factory is factory


def test_sync_has_factory_false_without_factory(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    assert repo.has_factory is False


def test_sync_maybe_factory_is_none_without_factory(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    assert repo.maybe_factory is None


def test_sync_factory_raises_without_factory(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(FactoryRequiredError, match="factory is required for this operation"):
        _ = repo.factory


def test_sync_for_repo_raises_without_factory(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    with pytest.raises(FactoryRequiredError, match="factory is required for this operation"):
        repo.for_repo(_OtherRepo)


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


def test_batched_purge_ids_rejects_invalid_batch_size(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="b1")
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=0)
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        repo.batched_purge_ids(criteria=[Widget.name.like("b%")], batch_size=-1)
    assert repo.count() == 1


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


def test_update_where_empty_values_is_no_op(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="stay")
    assert repo.update_where(criteria=[Widget.id == row.id], values={}) == 0
    assert repo.get(row.id).name == "stay"


def test_delete_where_accepts_bind_params(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="dw")
    assert repo.delete_where(criteria=[Widget.id == row.id], params={"p": 1}) == 1
    assert repo.get_by_id(row.id) is None


def test_delete_where_empty_criteria_is_no_op(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="stay")
    assert repo.delete_where(criteria=[]) == 0
    assert repo.count() == 1


def test_update_where_bulk_updates_matching_rows(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="join")
    assert repo.update_where(criteria=[Widget.id == row.id], values={"name": "updated"}) == 1
    assert repo.get(row.id).name == "updated"


def test_get_many_with_load_relations(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="loaded")
    loaded = repo.get_many([row.id], load_relations=[Load(Widget)])
    assert len(loaded) == 1
    assert loaded[0].name == "loaded"


def test_get_with_join_returns_related_rows(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    widget = repo.create(name="join")
    BaseRepository(Tag, sync_session).create(label="lbl")
    rows = repo.get_with_join(Tag, Widget.id == Tag.id, join_on=Widget.id == Tag.id)
    assert isinstance(rows, list)
    stmt = select(Widget).where(Widget.id == widget.id)
    repo._apply_load_relations(stmt, [Load(Widget)])


def test_fetch_sorted_mappings_without_sort(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="sorted")
    rows = repo.fetch_sorted_mappings(
        select(Widget.id),
        list_query=ListQuery(offset=0, limit=5),
        sort=None,
    )
    assert len(rows) >= 1


def test_filter_pagination_returns_expected_page(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    for i in range(3):
        repo.create(name=f"p{i}")
    assert len(repo.filter(page=2, limit=1)) == 1
    assert len(repo.get_all(page=1, limit=2)) == 2


def test_delete_all_removes_every_row(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="gone")
    deleted = repo.delete_all()
    assert deleted >= 1
    assert repo.count() == 0


def test_fetch_mappings_page_and_sorted_mappings(sync_session: Session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="sorted")
    from sqlalchemy import select as sa_select

    from sqlphilosophy.sorting import SortConfig, SortSpec

    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    rows = repo.fetch_sorted_mappings(
        sa_select(Widget.id, Widget.name),
        list_query=ListQuery(offset=0, limit=5),
        sort=sort,
    )
    assert rows
    page = repo.fetch_mappings_page(sa_select(Widget.id), limit=5, offset=0)
    assert page
