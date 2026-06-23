"""Last-mile sql and query coverage."""

from __future__ import annotations
from uuid import uuid4
import pytest

from conftest import Tag
from conftest import Widget
from sqlalchemy import literal_column
from sqlalchemy import select
from sqlphilosophy.sql import api_float
from sqlphilosophy.sql import api_int
from sqlphilosophy.sql import row_float
from sqlphilosophy.sql import row_json
from sqlphilosophy.sql import row_opt_float
from sqlphilosophy.sql import row_opt_json_object
from sqlphilosophy.sql import row_opt_uuid
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.repository import BaseRepository


def test_row_float_and_api_paths() -> None:
    assert row_float({"x": 1.0}, "x") == 1.0
    assert row_float({"x": 2}, "x") == 2.0
    assert row_opt_float({"x": 1.0}, "x") == 1.0
    with pytest.raises(TypeError):
        row_float({"x": "nope"}, "x")
    with pytest.raises(TypeError):
        row_opt_float({"x": "nope"}, "x")
    assert api_int({"x": 7}, "x") == 7
    assert api_float({"x": 2.5}, "x") == 2.5
    assert row_json({"x": True}, "x") is True
    with pytest.raises(TypeError):
        row_json({"x": {1: 2}}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": {1: 2}}, "x")


def test_row_opt_uuid_instance() -> None:
    uid = uuid4()
    assert row_opt_uuid({"x": uid}, "x") == uid
    with pytest.raises(TypeError):
        row_opt_json_object({"x": {1: "bad"}}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": []}, "x")
    assert row_opt_json_object({"x": {"ok": 1}}, "x") == {"ok": 1}


def test_sync_query_empty_from_and_distinct_where(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="w")
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_columns(Widget.id)
        .where(Widget.name == "w")
        .count()
    )
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .where(Widget.name == "w")
        .count_distinct(Widget.id)
    )


def test_sync_query_lateral_cte_and_count_froms(sync_session) -> None:
    BaseRepository(Widget, sync_session).create(name="lat")
    b = SqlAlchemyStatementBuilder(sync_session, Widget)
    b.as_lateral("w")
    b.as_cte("w")
    (
        SqlAlchemyStatementBuilder(sync_session, Widget)
        .select_entity()
        .select_from(Widget)
        .join(Tag, Widget.id == Tag.id)
        .count()
    )
    empty = SqlAlchemyStatementBuilder(sync_session, Widget)
    empty._stmt = select(literal_column("1"))
    empty.count()


def test_sync_repository_delete_where_params(sync_session) -> None:
    repo = BaseRepository(Widget, sync_session)
    row = repo.create(name="dw")
    assert repo.delete_where(criteria=[Widget.id == row.id], params={"p": 1}) == 1
    with pytest.raises(ValueError, match="page must be >= 1"):
        repo.get_all(page=0)
