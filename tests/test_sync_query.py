"""Sync SqlAlchemyStatementBuilder behavior."""

from __future__ import annotations

import pytest
from sqlalchemy import literal_column, select
from sqlalchemy.dialects import postgresql

from conftest import Child, Parent, Tag, Widget
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, cte_from, lateral_from
from sqlphilosophy.sync.repository import BaseRepository


def test_query_builder_chain_and_terminals(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    repo.create(name="z")
    repo.create(name="a")
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity()
    scalars = builder.where(Widget.active.is_(True)).order_by(Widget.name).limit(10).offset(0).scalars().all()
    assert len(scalars) == 2
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.active.is_(True))
        .scalars()
        .first()
        is not None
    )
    assert SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).limit(1).scalar() is not None
    mappings = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().mappings().all()
    assert mappings
    assert SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.active.is_(True)).count() == 2
    assert SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).count_distinct(Widget.id) == 2


def test_query_builder_one_or_none_via_scalars(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="only")
    found = SqlAlchemyStatementBuilder(sync_session, Widget).filter_by(name="only").scalars().first()
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


def test_fetch_page_does_not_mutate_builder(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    for i in range(5):
        repo.create(name=f"n{i}")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.active.is_(True))
    rows, total = builder.fetch_page(ListQuery(offset=0, limit=2), sort=sort)
    assert total == 5
    assert len(rows) == 2
    assert len(builder.scalars().all()) == 5
    assert builder.count() == 5


def test_limit_offset_still_mutates_builder(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    for i in range(4):
        repo.create(name=f"n{i}")
    builder = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().order_by(Widget.id)
    builder.limit(2).offset(1)
    assert len(builder.scalars().all()) == 2


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
        .distinct()
        .group_by(Widget.id)
        .correlate(Widget)
        .correlate_except(Tag)
    )
    assert b.build_select() is not None


def test_distinct_columns_compile_postgresql_distinct_on(sync_session) -> None:
    stmt = SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().distinct(Parent.id).build_select()
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "DISTINCT ON (parent.id)" in compiled


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


def test_count_with_implicit_join_onclause(sync_session) -> None:
    parent = Parent()
    sync_session.add(parent)
    sync_session.flush()
    sync_session.add(Child(parent_id=parent.id))
    sync_session.flush()
    assert SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().join(Child).count() >= 1
    assert SqlAlchemyStatementBuilder(sync_session, Parent).select_entity().outerjoin(Child).count() >= 1


def test_count_with_for_update_of_entity(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="lock")
    assert SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().with_for_update(of=Widget).count() == 1


def test_count_after_explicit_select_from_and_join(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="lat")
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
        .count()
    )
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id, Tag.id)
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
        .count()
    )


def test_count_on_literal_select_without_from(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="cnt")
    empty = SqlAlchemyStatementBuilder(sync_session, Widget)
    empty._stmt = select(literal_column("1"))
    assert empty.count() == 1


def test_builder_as_lateral_and_as_cte(sync_session) -> None:
    b = SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id)
    assert b.as_lateral("w").name == "w"
    assert b.as_cte("w").name == "w"


def test_count_distinct_after_where_filter(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="w")
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget).select_columns(Widget.id).where(Widget.name == "w").count()
        == 1
    )
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.name == "w")
        .count_distinct(Widget.id)
        == 1
    )


def test_fetch_page_rejects_negative_offset(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="q1")
    b2 = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.name.isnot(None))
    rows, total = b2.fetch_page(ListQuery(offset=0, limit=1))
    assert total >= 1
    assert len(rows) == 1
    with pytest.raises(ValueError, match="offset must be >= 0"):
        b2.fetch_page(ListQuery(offset=-1, limit=1))


def test_apply_sort_then_count_and_fetch_page(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="c1")
    BaseRepository(Widget, sync_session).create(name="c2")
    sort = SortConfig(
        default=SortSpec("name", "asc"),
        columns={"name": {"asc": Widget.name, "desc": Widget.name.desc()}},
    )
    b = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().apply_sort(sort, {"name": "desc"})
    assert b.count() == 2
    assert b.count_distinct(Widget.id) == 2
    rows, total = b.fetch_page(ListQuery(offset=0, limit=1))
    assert total == 2
    assert len(rows) == 1
    assert b.build_select() is not None


def test_query_builder_extended_join_and_correlate(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="q1")
    BaseRepository(Widget, sync_session).create(name="q2")
    b = SqlAlchemyStatementBuilder(sync_session, Widget)
    b.select_table().join(Tag, Widget.id == Tag.id)
    assert (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .outerjoin(Tag, Widget.id == Tag.id)
        .correlate(Widget)
        .correlate_except(Tag)
        .with_for_update(skip_locked=True)
        .count()
        >= 0
    )
    b2 = SqlAlchemyStatementBuilder(sync_session, Widget).select_entity().where(Widget.name.isnot(None))
    rows, total = b2.fetch_page(ListQuery(offset=0, limit=1))
    assert total >= 1
    assert len(rows) == 1
