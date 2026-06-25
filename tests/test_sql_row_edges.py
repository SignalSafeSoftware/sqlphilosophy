"""Row helper edge cases for 100% sql.py coverage."""

from __future__ import annotations
from uuid import uuid4
import pytest
from sqlphilosophy.sql import api_int
from sqlphilosophy.sql import row_float
from sqlphilosophy.sql import row_json
from sqlphilosophy.sql import row_json_object
from sqlphilosophy.sql import row_opt_bool
from sqlphilosophy.sql import row_opt_float
from sqlphilosophy.sql import row_opt_int
from sqlphilosophy.sql import row_opt_json_object
from sqlphilosophy.sql import row_opt_str
from sqlphilosophy.sql import row_opt_uuid
from sqlphilosophy.sql import row_str


def test_row_opt_int_bool_raises() -> None:
    with pytest.raises(TypeError):
        row_opt_int({"x": True}, "x")


def test_row_opt_str_types() -> None:
    assert row_opt_str({"x": 1}, "x") == "1"
    assert row_opt_str({"x": False}, "x") == "False"


def test_row_float_int_path() -> None:
    assert row_float({"x": 2}, "x") == pytest.approx(2.0)


def test_row_opt_float_int_path() -> None:
    assert row_opt_float({"x": 2}, "x") == pytest.approx(2.0)


def test_row_opt_bool_true() -> None:
    assert row_opt_bool({"x": False}, "x") is False


def test_row_json_list() -> None:
    assert row_json({"x": [1, 2]}, "x") == [1, 2]


def test_row_json_object_bad_keys() -> None:
    with pytest.raises(TypeError):
        row_json_object({"x": {1: 2}}, "x")
    with pytest.raises(TypeError):
        row_opt_json_object({"x": {1: 2}}, "x")


def test_row_opt_uuid_string() -> None:
    uid = uuid4()
    assert row_opt_uuid({"x": str(uid)}, "x") == uid


def test_row_str_date_types() -> None:
    from datetime import date
    from datetime import datetime

    assert row_str({"x": date.today()}, "x")
    assert row_str({"x": datetime.now()}, "x")


def test_api_int_bool_path() -> None:
    assert api_int({"x": False}, "x") == 0
