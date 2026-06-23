"""SQL helper functions."""

from __future__ import annotations
from datetime import date
from datetime import datetime
from uuid import UUID
from uuid import uuid4
import pytest

from conftest import Widget
from sqlalchemy import column
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec
from sqlphilosophy.sql import api_float
from sqlphilosophy.sql import api_int
from sqlphilosophy.sql import apply_mappings_page
from sqlphilosophy.sql import col_eq
from sqlphilosophy.sql import col_icontains
from sqlphilosophy.sql import col_range
from sqlphilosophy.sql import combine_and
from sqlphilosophy.sql import count_from_subquery
from sqlphilosophy.sql import count_from_table
from sqlphilosophy.sql import delete_by_ids
from sqlphilosophy.sql import delete_by_ids_model
from sqlphilosophy.sql import expanding_in_param
from sqlphilosophy.sql import get_column_value
from sqlphilosophy.sql import get_sort_column
from sqlphilosophy.sql import literal_order_expr
from sqlphilosophy.sql import merge_criteria
from sqlphilosophy.sql import order_by_allowlist
from sqlphilosophy.sql import order_expr_from_sort
from sqlphilosophy.sql import partial_update
from sqlphilosophy.sql import partial_update_model
from sqlphilosophy.sql import row_bool
from sqlphilosophy.sql import row_float
from sqlphilosophy.sql import row_int
from sqlphilosophy.sql import row_json
from sqlphilosophy.sql import row_json_object
from sqlphilosophy.sql import row_mapping
from sqlphilosophy.sql import row_mapping_opt
from sqlphilosophy.sql import row_opt_bool
from sqlphilosophy.sql import row_opt_float
from sqlphilosophy.sql import row_opt_int
from sqlphilosophy.sql import row_opt_json_object
from sqlphilosophy.sql import row_opt_str
from sqlphilosophy.sql import row_opt_uuid
from sqlphilosophy.sql import row_str
from sqlphilosophy.sql import row_uuid
from sqlphilosophy.sql import rows_mapping
from sqlphilosophy.sql import select_page_from_table
from sqlphilosophy.sql import sql_table


def test_row_coercions() -> None:
    row = {
        "i": 1,
        "f": 1.5,
        "s": "x",
        "b": True,
        "ni": None,
        "uid": uuid4(),
        "json": {"a": 1},
        "lst": [1],
        "bytes": b"hi",
        "dt": datetime.now(),
        "d": date.today(),
    }
    assert row_int(row, "i") == 1
    assert row_opt_int(row, "ni") is None
    assert row_str(row, "s") == "x"
    assert row_str(row, "i") == "1"
    assert row_str(row, "bytes") == "hi"
    assert row_opt_str(row, "ni") is None
    assert row_bool(row, "b") is True
    assert row_opt_bool(row, "ni") is None
    assert row_float(row, "f") == 1.5
    assert row_opt_float(row, "ni") is None
    assert row_json(row, "json") == {"a": 1}
    assert row_json_object(row, "json") == {"a": 1}
    assert row_opt_json_object(row, "ni") is None
    assert isinstance(row_uuid(row, "uid"), UUID)
    assert row_opt_uuid(row, "ni") is None
    with pytest.raises(TypeError):
        row_int(row, "b")
    with pytest.raises(TypeError):
        row_bool(row, "i")
    with pytest.raises(TypeError):
        row_json(row, "dt")
    with pytest.raises(TypeError):
        row_json_object(row, "lst")
    bad = {"bad": {1: 2}}
    with pytest.raises(TypeError):
        row_json_object(bad, "bad")


def test_api_int_float_defaults() -> None:
    assert api_int({}, "missing") == 0
    assert api_int({"x": "nope"}, "x") == 0
    assert api_int({"x": True}, "x") == 1
    assert api_float({}, "missing") == 0.0
    assert api_float({"x": "nope"}, "x") == 0.0
    assert api_float({"x": 2}, "x") == 2.0
    assert api_int({"x": object()}, "x") == 0


def test_row_mapping_helpers(sync_session: Session) -> None:
    row = Widget(name="map")
    sync_session.add(row)
    sync_session.flush()
    mapped = get_column_value(row)
    assert mapped["name"] == "map"
    assert row_mapping(None) == {}
    assert row_mapping_opt(None) is None
    assert rows_mapping([{"id": 1}]) == [{"id": 1}]


def test_apply_mappings_page(sync_session: Session) -> None:
    w = Widget(name="page")
    sync_session.add(w)
    sync_session.flush()
    stmt = select(Widget.id, Widget.name)
    rows = apply_mappings_page(sync_session, stmt, limit=10, offset=0)
    assert rows
    with pytest.raises(ValueError):
        apply_mappings_page(sync_session, stmt, limit=-1, offset=0)


def test_get_sort_column() -> None:
    sort = SortConfig(
        default=SortSpec("id", "asc"),
        columns={"id": {"asc": "t.id ASC", "desc": "t.id DESC"}},
        literal_sql=True,
    )
    assert get_sort_column(sort, {"id": "asc"}) is not None


def test_partial_update_and_delete(sync_session: Session) -> None:
    row = Widget(name="upd")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update(
            sync_session,
            "widget",
            row.id,
            {"name": "new"},
            frozenset({"name"}),
        )
        == 1
    )
    assert (
        partial_update_model(sync_session, Widget, row.id, {"name": "again"}, frozenset({"name"}))
        == 1
    )
    assert partial_update(sync_session, "widget", row.id, {}, frozenset({"name"})) == 0
    row2 = Widget(name="del2")
    sync_session.add(row2)
    sync_session.flush()
    assert delete_by_ids(sync_session, "widget", [row2.id]) == 1
    assert delete_by_ids_model(sync_session, Widget, []) == 0


def test_criteria_helpers() -> None:
    expr, params = col_eq("t.name", "name", "x")
    assert params == {"name": "x"}
    expr2, params2 = col_icontains("t.name", "name", "x")
    assert expr2 is not None and params2 is not None and "name" in params2
    assert col_icontains("t.name", "name", "  ") is None
    expr3, params3 = col_range("t.id", "lo", ">=", 1)
    assert params3["lo"] == 1
    merged_crit, merged_params = merge_criteria(([expr], params), ([expr3], params3))
    assert merged_crit
    assert merged_params
    assert combine_and(None, expr) is expr
    assert combine_and() is None
    order = order_by_allowlist(
        "name",
        {"name": "name ASC"},
        allowlist=frozenset({"name"}),
    )
    assert order is not None
    order2 = order_expr_from_sort(
        "name", "desc", columns={"name": {"asc": "n ASC", "desc": "n DESC"}}
    )
    assert order2 is not None
    with pytest.raises(ValueError, match="unsupported operator"):
        col_range("t.id", "lo", "!=", 1)


def test_expanding_in_param() -> None:
    bind, params = expanding_in_param("ids", [1, 2])
    assert params["ids"] == ["1", "2"]
    assert bind is not None


def test_count_and_select_page(sync_session: Session) -> None:
    w = Widget(name="count")
    sync_session.add(w)
    sync_session.flush()
    tbl = sql_table("widget", "id", "name")
    crit = [column("name") == "count"]
    assert count_from_table(sync_session, tbl, crit, {"name": "count"}) >= 0
    subq = select(Widget.id).subquery()
    assert count_from_subquery(sync_session, subq) >= 1
    rows = select_page_from_table(
        sync_session,
        tbl,
        crit,
        {"name": "count"},
        order_by=literal_order_expr("id ASC"),
        limit=5,
        offset=0,
    )
    assert isinstance(rows, list)


def test_sql_table() -> None:
    t = sql_table("demo", "id", "name")
    assert t.name == "demo"
