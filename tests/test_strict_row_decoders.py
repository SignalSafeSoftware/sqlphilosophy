from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import uuid4

import pytest

from sqlphilosophy.strict import (
    is_strict_json_value,
    strict_row_bool,
    strict_row_date,
    strict_row_datetime,
    strict_row_enum,
    strict_row_float,
    strict_row_int,
    strict_row_json,
    strict_row_json_object,
    strict_row_optional,
    strict_row_str,
    strict_row_str_list,
    strict_row_uuid,
)


class Colour(StrEnum):
    BLUE = "blue"


def test_strict_decoders_accept_exact_values_and_enum_strings() -> None:
    uid = uuid4()
    timestamp = datetime(2026, 9, 8, tzinfo=UTC)
    row = {
        "int": 3,
        "str": "value",
        "bool": True,
        "float": 1.5,
        "datetime": timestamp,
        "date": date(2026, 9, 8),
        "uuid": uid,
        "enum": "blue",
        "enum_value": Colour.BLUE,
        "strings": ["a", "b"],
        "json": {"nested": [True, None, 2.5]},
    }

    assert strict_row_int(row, "int") == 3
    assert strict_row_str(row, "str") == "value"
    assert strict_row_bool(row, "bool") is True
    assert strict_row_float(row, "float") == 1.5
    assert strict_row_datetime(row, "datetime") == timestamp
    assert strict_row_date(row, "date") == date(2026, 9, 8)
    assert strict_row_uuid(row, "uuid") == uid
    assert strict_row_enum(row, "enum", Colour) is Colour.BLUE
    assert strict_row_enum(row, "enum_value", Colour) is Colour.BLUE
    assert strict_row_str_list(row, "strings") == ["a", "b"]
    assert strict_row_json(row, "json") == {"nested": [True, None, 2.5]}
    assert strict_row_json_object(row, "json") == row["json"]


def test_strict_decoders_reject_coercion_and_invalid_json() -> None:
    invalid_rows = [
        (strict_row_int, {"x": True}),
        (strict_row_str, {"x": 1}),
        (strict_row_bool, {"x": 1}),
        (strict_row_float, {"x": 1}),
        (strict_row_datetime, {"x": date.today()}),
        (strict_row_date, {"x": datetime.now()}),
        (strict_row_uuid, {"x": str(uuid4())}),
        (strict_row_str_list, {"x": ["ok", 1]}),
    ]
    for decoder, row in invalid_rows:
        with pytest.raises(TypeError):
            decoder(row, "x")

    with pytest.raises(TypeError):
        strict_row_enum({"x": "red"}, "x", Colour)
    with pytest.raises(TypeError):
        strict_row_enum({"x": 1}, "x", Colour)
    with pytest.raises(TypeError):
        strict_row_float({"x": float("nan")}, "x")
    with pytest.raises(TypeError):
        strict_row_json({"x": {"bad": object()}}, "x")
    with pytest.raises(TypeError):
        strict_row_json({"x": {1: "bad"}}, "x")
    with pytest.raises(TypeError):
        strict_row_json({"x": (1, 2)}, "x")
    with pytest.raises(TypeError):
        strict_row_json_object({"x": [1]}, "x")
    with pytest.raises(KeyError):
        strict_row_int({}, "missing")


def test_strict_json_guard_and_optional_decoder() -> None:
    assert is_strict_json_value(None)
    assert is_strict_json_value(False)
    assert is_strict_json_value(1)
    assert is_strict_json_value("text")
    assert is_strict_json_value([{"ok": 1}])
    assert not is_strict_json_value(float("inf"))
    assert not is_strict_json_value({"bad": object()})

    assert strict_row_optional({}, "missing", strict_row_int) is None
    assert strict_row_optional({"x": None}, "x", strict_row_int) is None
    assert strict_row_optional({"x": 4}, "x", strict_row_int) == 4
    with pytest.raises(TypeError):
        strict_row_optional({"x": "4"}, "x", strict_row_int)
