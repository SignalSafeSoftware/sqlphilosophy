"""SQL helper functions."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import column, select
from sqlalchemy.orm import Session

from conftest import Tag, UpdatableTag, Widget
from sqlphilosophy._repository_shared import PartialUpdatePlan
from sqlphilosophy.sorting import SortConfig, SortSpec
from sqlphilosophy.sql import (
    api_float,
    api_int,
    apply_mappings_page,
    apply_writable_update,
    col_eq,
    col_icontains,
    col_range,
    combine_and,
    count_from_subquery,
    count_from_table,
    delete_by_ids,
    delete_by_ids_model,
    expanding_in_param,
    get_column_value,
    get_sort_column,
    literal_order_expr,
    merge_criteria,
    order_by_allowlist,
    order_expr_from_sort,
    partial_update,
    partial_update_model,
    row_bool,
    row_float,
    row_int,
    row_json,
    row_json_object,
    row_mapping,
    row_mapping_opt,
    row_opt_bool,
    row_opt_float,
    row_opt_int,
    row_opt_json_object,
    row_opt_str,
    row_opt_uuid,
    row_str,
    row_uuid,
    rows_mapping,
    select_page_from_table,
    sql_table,
)


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
    assert row_float(row, "f") == pytest.approx(1.5)
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
    assert api_float({}, "missing") == pytest.approx(0.0)
    assert api_float({"x": "nope"}, "x") == pytest.approx(0.0)
    assert api_float({"x": 2}, "x") == pytest.approx(2.0)
    assert api_int({"x": object()}, "x") == 0


def test_get_column_value_unmapped() -> None:
    with pytest.raises(TypeError, match="not a mapped SQLAlchemy entity"):
        get_column_value(object())


def test_row_mapping_helpers(sync_session: Session) -> None:
    row = Widget(name="map")
    sync_session.add(row)
    sync_session.flush()
    mapped = get_column_value(row)
    assert mapped["name"] == "map"
    assert row_mapping(None) == {}
    assert row_mapping_opt(None) is None
    assert rows_mapping([{"id": 1}]) == [{"id": 1}]


def test_row_mapping_unwraps_duck_typed_entity() -> None:
    from types import SimpleNamespace
    from typing import ClassVar
    from unittest.mock import patch

    class FakeMapper:
        column_attrs: ClassVar[list[SimpleNamespace]] = [
            SimpleNamespace(key="id"),
            SimpleNamespace(key="email"),
        ]

    class FakeEntity:
        __mapper__ = object()
        id = 5
        email = "x@y.z"

    class LabeledKey:
        key = "title"

        def __eq__(self, other: object) -> bool:
            return isinstance(other, LabeledKey) and self.key == other.key

        def __hash__(self) -> int:
            return hash("title")

    entity = FakeEntity()
    labeled = LabeledKey()
    fake_insp = SimpleNamespace(mapper=FakeMapper())
    with patch("sqlphilosophy.sql.sa_inspect", return_value=fake_insp):
        row = SimpleNamespace(_mapping={"user": entity, labeled: "Phish"})
        mapped = row_mapping(row)
    assert mapped["id"] == 5
    assert mapped["email"] == "x@y.z"
    assert mapped["title"] == "Phish"


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
    assert partial_update_model(sync_session, Widget, row.id, {"name": "again"}, frozenset({"name"})) == 1
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
    assert expr2 is not None
    assert params2 is not None
    assert "name" in params2
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
    order2 = order_expr_from_sort("name", "desc", columns={"name": {"asc": "n ASC", "desc": "n DESC"}})
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


class _Key:
    def __init__(self, key: str) -> None:
        self.key = key


def test_row_mapping_normalizes_key_objects_and_result_rows(sync_session: Session) -> None:
    sync_session.add(Widget(name="rowmap"))
    sync_session.flush()
    result = sync_session.execute(select(Widget.id, Widget.name)).first()
    assert result is not None
    mapped = row_mapping(result)
    assert mapped["name"] == "rowmap"
    assert row_mapping({_Key("id"): 1, "name": "x"})["id"] == 1


def test_row_mapping_unwraps_orm_instance(sync_session: Session) -> None:
    row = Widget(name="orm")
    sync_session.add(row)
    sync_session.flush()
    assert row_mapping(row)["name"] == "orm"


def test_row_opt_int_coerces_numeric_strings_and_floats() -> None:
    assert row_opt_int({"n": 1.0}, "n") == 1
    assert row_opt_int({"n": "2"}, "n") == 2
    assert row_opt_int({"x": 5}, "x") == 5
    with pytest.raises(TypeError):
        row_opt_int({"n": object()}, "n")
    with pytest.raises(TypeError):
        row_opt_int({"x": True}, "x")


def test_row_opt_str_accepts_bytes_and_rejects_bad_types() -> None:
    assert row_opt_str({"b": b"bytes"}, "b") == "bytes"
    assert row_opt_str({"x": "ok"}, "x") == "ok"
    assert row_opt_str({"x": 1}, "x") == "1"
    assert row_opt_str({"x": False}, "x") == "False"
    with pytest.raises(TypeError):
        row_opt_str({"n": object()}, "n")


def test_row_coercion_rejects_invalid_types() -> None:
    with pytest.raises((TypeError, ValueError)):
        row_int({"x": "bad"}, "x")
    with pytest.raises(TypeError):
        row_int({"x": object()}, "x")
    with pytest.raises(TypeError):
        row_str({"x": object()}, "x")
    with pytest.raises(TypeError):
        row_opt_bool({"x": 1}, "x")
    with pytest.raises(TypeError):
        row_float({"x": True}, "x")
    with pytest.raises(TypeError):
        row_opt_float({"x": True}, "x")
    with pytest.raises(TypeError):
        row_uuid({"x": 1}, "x")
    with pytest.raises((TypeError, ValueError)):
        row_opt_uuid({"x": 1}, "x")
    with pytest.raises(TypeError):
        row_json({"x": datetime.now()}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": []}, "x")


def test_row_coercion_accepts_common_scalar_variants() -> None:
    uid = uuid4()
    row = {
        "i": 2.0,
        "s": 1,
        "b": False,
        "f": 3,
        "uid": str(uid),
        "d": date.today(),
    }
    assert row_int(row, "i") == 2
    assert row_str(row, "s") == "1"
    assert row_opt_int(row, "missing") is None
    assert row_opt_str(row, "missing") is None
    assert row_opt_bool(row, "b") is False
    assert row_opt_float(row, "f") == pytest.approx(3.0)
    assert row_uuid(row, "uid") == uid
    assert row_float({"x": 2}, "x") == pytest.approx(2.0)
    assert row_opt_float({"x": 2}, "x") == pytest.approx(2.0)
    assert row_json({"x": [1, 2]}, "x") == [1, 2]
    assert row_opt_uuid({"x": uid}, "x") == uid
    assert row_opt_uuid({"x": str(uid)}, "x") == uid


def test_row_float_and_api_helpers_coerce_or_default() -> None:
    assert row_float({"x": 1.0}, "x") == pytest.approx(1.0)
    assert row_float({"x": 2}, "x") == pytest.approx(2.0)
    assert row_opt_float({"x": 1.0}, "x") == pytest.approx(1.0)
    with pytest.raises(TypeError):
        row_float({"x": "nope"}, "x")
    with pytest.raises(TypeError):
        row_opt_float({"x": "nope"}, "x")
    assert api_int({"x": 7}, "x") == 7
    assert api_int({"x": 1.5}, "x") == 1
    assert api_int({"x": "3"}, "x") == 3
    assert api_int({"x": False}, "x") == 0
    assert api_float({"x": 2.5}, "x") == pytest.approx(2.5)
    assert api_float({"x": True}, "x") == pytest.approx(1.0)
    assert api_float({"x": "2.5"}, "x") == pytest.approx(2.5)
    assert api_float({"x": object()}, "x") == pytest.approx(0.0)
    assert row_json({"x": True}, "x") is True
    with pytest.raises(TypeError):
        row_json({"x": {1: 2}}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": {1: 2}}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": {1: "bad"}}, "x")
    assert row_opt_json_object({"x": {"ok": 1}}, "x") == {"ok": 1}


def test_delete_by_ids_empty_list_returns_zero() -> None:
    assert delete_by_ids(Session(), "widget", []) == 0


def test_select_page_from_table_without_where_clause(sync_session: Session) -> None:
    sync_session.add(Widget(name="page2"))
    sync_session.flush()
    tbl = sql_table("widget", "id", "name")
    rows = select_page_from_table(
        sync_session,
        tbl,
        [],
        {},
        order_by=Widget.id,  # type: ignore[arg-type]
        limit=5,
        offset=0,
    )
    assert len(rows) >= 1
    assert rows[0]["name"] == "page2"


def test_count_from_table_without_criteria(sync_session: Session) -> None:
    sync_session.add(Widget(name="c"))
    sync_session.flush()
    tbl = sql_table("widget", "id", "name")
    assert count_from_table(sync_session, tbl, [], {}) >= 1


def test_apply_mappings_page_rejects_negative_offset(sync_session: Session) -> None:
    with pytest.raises(ValueError, match="offset must be >= 0"):
        apply_mappings_page(sync_session, select(Widget.id), limit=1, offset=-1)


def test_col_range_lte_and_merge_criteria_none() -> None:
    crit, params = col_range("t.id", "hi", "<=", 9)
    assert params["hi"] == 9
    criteria, _ = merge_criteria(None, ([crit], params))
    assert criteria


def test_order_by_allowlist_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="invalid order key"):
        order_by_allowlist("bad", {"name": "n ASC"}, allowlist=frozenset({"name"}))


def test_partial_update_model_audit_path_with_extra_values(sync_session: Session) -> None:
    tag = Tag(label="touch")
    sync_session.add(tag)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Tag,
            tag.id,
            {"label": "t2"},
            frozenset({"label"}),
            extra_values={"label": "t3"},
        )
        == 1
    )
    sync_session.refresh(tag)
    assert tag.label == "t3"


def test_partial_update_model_core_non_audit(sync_session: Session) -> None:
    tag = Tag(label="core")
    sync_session.add(tag)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Tag,
            tag.id,
            {"label": "updated"},
            frozenset({"label"}),
            touch_updated_on=False,
        )
        == 1
    )
    sync_session.refresh(tag)
    assert tag.label == "updated"


def test_partial_update_model_skips_missing_row_and_empty_writable(sync_session: Session) -> None:
    row = Widget(name="touch")
    sync_session.add(row)
    sync_session.flush()
    assert partial_update_model(sync_session, Widget, 9999, {"name": "x"}, frozenset({"name"})) == 0
    assert partial_update_model(sync_session, Widget, row.id, {"name": "x"}, frozenset()) == 0
    tag = Tag(label="e")
    sync_session.add(tag)
    sync_session.flush()
    assert partial_update_model(sync_session, Tag, tag.id, {"label": "x"}, frozenset()) == 0


def test_partial_update_model_rejects_unexpected_plan_action(
    sync_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = Widget(name="guard")
    sync_session.add(row)
    sync_session.flush()

    def bad_plan(*_args: object, **_kwargs: object) -> PartialUpdatePlan:
        return PartialUpdatePlan("invalid", {"name": "y"})  # type: ignore[arg-type]

    monkeypatch.setattr("sqlphilosophy.sql.plan_partial_update", bad_plan)
    with pytest.raises(RuntimeError, match="unexpected partial update plan action"):
        partial_update_model(sync_session, Widget, row.id, {"name": "y"}, frozenset({"name"}))


def test_partial_update_model_audit_touch_and_extra_values(sync_session: Session) -> None:
    row = Widget(name="touch")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            Widget,
            row.id,
            {"name": "touched"},
            frozenset({"name"}),
            touch_updated_on=True,
            extra_values={"active": False},
        )
        == 1
    )
    sync_session.refresh(row)
    assert row.name == "touched"
    assert row.active is False


def test_partial_update_model_touch_updated_on_sets_timestamp(sync_session: Session) -> None:
    row = UpdatableTag(label="u")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update_model(
            sync_session,
            UpdatableTag,
            row.id,
            {"label": "u2"},
            frozenset({"label"}),
            touch_updated_on=True,
        )
        == 1
    )
    sync_session.refresh(row)
    assert row.label == "u2"
    assert row.updated_on is not None


def test_partial_update_core_table_with_touch_and_extra(sync_session: Session) -> None:
    row = Widget(name="core")
    sync_session.add(row)
    sync_session.flush()
    assert (
        partial_update(
            sync_session,
            "widget",
            row.id,
            {"name": "core2"},
            frozenset({"name"}),
            touch_updated_on=True,
            extra_values={"active": False},
        )
        == 1
    )
    sync_session.refresh(row)
    assert row.name == "core2"
    assert row.active is False


def test_apply_writable_update_filters_to_writable_fields(sync_session: Session) -> None:
    row = Widget(name="writable")
    sync_session.add(row)
    sync_session.flush()
    apply_writable_update(sync_session, Widget, row.id, {"name": "w2"}, frozenset({"name"}))
    sync_session.refresh(row)
    assert row.name == "w2"
    apply_writable_update(sync_session, Widget, row.id, {"name": "ignored"}, frozenset())
    sync_session.refresh(row)
    assert row.name == "w2"
