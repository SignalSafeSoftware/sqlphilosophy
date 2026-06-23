"""Sync SqlAlchemyStatementBuilder behavior."""

from __future__ import annotations
import pytest

from conftest import Tag
from conftest import Widget
from sqlalchemy.dialects import postgresql
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec
from sqlphilosophy.sync.query import cte_from
from sqlphilosophy.sync.query import lateral_from
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_query_builder_chain_and_terminals(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="z")
    repo.create(name="a")
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity()
    scalars = (
        builder.where(Widget.active.is_(True))
        .order_by(Widget.name)
        .limit(10)
        .offset(0)
        .scalars()
        .all()
    )
    assert len(scalars) == 2
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .scalars()
        .first()
        is not None
    )
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).limit(1).scalar()
        is not None
    )
    mappings = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().mappings().all()
    assert mappings
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .count()
        == 2
    )
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id)
        .count_distinct(Widget.id)
        == 2
    )


def test_query_builder_one_or_none_via_scalars(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="only")
    found = (
        SqlAlchemyStatementBuilder(sync_session, Widget).filter_by(name="only").scalars().first()
    )
    assert found.id == row.id


def test_query_builder_mappings_terminals(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="m")
    b = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id, Widget.name)
    assert b.mappings().all()
    assert b.mappings().first() is not None
    assert b.mappings().one()["name"] == "m"


def test_fetch_page(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    for i in range(5):
        repo.create(name=f"n{i}")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    rows, total = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id, Widget.name)
        .fetch_page(ListQuery(offset=0, limit=2), sort=sort)
    )
    assert total == 5
    assert len(rows) == 2


def test_limit_offset_validation(sync_session) -> None:
    b = SqlAlchemyStatementBuilder(sync_session, Widget)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.limit(-1)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b.offset(-1)
    with pytest.raises(ValueError, match="limit must be >= 0"):
        b.fetch_page(ListQuery(offset=0, limit=-1), sort=None)


def test_join_distinct_group_by(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="j")
    BaseRepository(Tag, sync_session).create(label="t")
    b = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .join(Tag, Widget.id == Tag.id, isouter=True)
        .distinct(Widget.id)
        .group_by(Widget.id)
        .correlate(Widget)
        .correlate_except(Tag)
    )
    assert b.build_select() is not None


def test_lateral_and_cte_helpers(sync_session) -> None:
    b = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id)
    lateral = lateral_from(b.build_select(), "u")
    assert "LATERAL" in str(lateral.compile(dialect=postgresql.dialect()))
    cte = cte_from(b.build_select(), "w")
    assert cte.name == "w"


def test_with_for_update_and_params(sync_session) -> None:
    b = (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .with_for_update(of=Widget, skip_locked=True)
        .with_params({"x": 1})
    )
    assert b.build_select() is not None


def test_statement_via_repository_factory(sync_session) -> None:
    from sqlphilosophy.sync.protocols import RepositoryFactory

    class FakeFactory(RepositoryFactory):
        def __init__(self, session) -> None:
            self._session = session
            self.created: list[type] = []

        @property
        def session(self):
            return self._session

        def create_statement(self, model: type) -> SqlAlchemyStatementBuilder:
            self.created.append(model)
            return SqlAlchemyStatementBuilder(self._session, model)

        def get_repository(self, repo_class: type):
            return repo_class(self._session, self)

    factory = FakeFactory(sync_session)
    repo = BaseRepository(Widget, sync_session, factory)
    stmt = repo.statement()
    assert isinstance(stmt, SqlAlchemyStatementBuilder)
    assert Widget in factory.created
