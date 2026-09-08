"""Opt-in, non-coercing row decoders for repository boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime
from enum import Enum
from math import isfinite
from typing import TypeGuard
from uuid import UUID

from sqlphilosophy.types import JSONValue

__all__ = [
    "is_strict_json_value",
    "strict_row_bool",
    "strict_row_date",
    "strict_row_datetime",
    "strict_row_enum",
    "strict_row_float",
    "strict_row_int",
    "strict_row_json",
    "strict_row_json_object",
    "strict_row_optional",
    "strict_row_str",
    "strict_row_str_list",
    "strict_row_uuid",
]

Row = Mapping[str, object]


def _required(row: Row, key: str) -> object:
    return row[key]


def _type_error(key: str, expected: str, value: object) -> TypeError:
    return TypeError(f"expected strict {expected} for {key!r}, got {type(value).__name__}")


def strict_row_int(row: Row, key: str) -> int:
    value = _required(row, key)
    if type(value) is not int:
        raise _type_error(key, "int", value)
    return value


def strict_row_str(row: Row, key: str) -> str:
    value = _required(row, key)
    if type(value) is not str:
        raise _type_error(key, "str", value)
    return value


def strict_row_bool(row: Row, key: str) -> bool:
    value = _required(row, key)
    if type(value) is not bool:
        raise _type_error(key, "bool", value)
    return value


def strict_row_float(row: Row, key: str) -> float:
    value = _required(row, key)
    if type(value) is not float or not isfinite(value):
        raise _type_error(key, "finite float", value)
    return value


def strict_row_datetime(row: Row, key: str) -> datetime:
    value = _required(row, key)
    if type(value) is not datetime:
        raise _type_error(key, "datetime", value)
    return value


def strict_row_date(row: Row, key: str) -> date:
    value = _required(row, key)
    if type(value) is not date:
        raise _type_error(key, "date", value)
    return value


def strict_row_uuid(row: Row, key: str) -> UUID:
    value = _required(row, key)
    if not isinstance(value, UUID):
        raise _type_error(key, "UUID", value)
    return value


def strict_row_enum[EnumT: Enum](row: Row, key: str, enum_type: type[EnumT]) -> EnumT:
    value = _required(row, key)
    if isinstance(value, enum_type):
        return value
    if type(value) is str:
        try:
            return enum_type(value)
        except ValueError as error:
            raise _type_error(key, enum_type.__name__, value) from error
    raise _type_error(key, enum_type.__name__, value)


def strict_row_str_list(row: Row, key: str) -> list[str]:
    value = _required(row, key)
    if type(value) is not list or not all(type(item) is str for item in value):
        raise _type_error(key, "list[str]", value)
    return value


def is_strict_json_value(value: object) -> TypeGuard[JSONValue]:
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) is float:
        return isfinite(value)
    if type(value) is list:
        return all(is_strict_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and is_strict_json_value(item) for key, item in value.items())
    return False


def strict_row_json(row: Row, key: str) -> JSONValue:
    value = _required(row, key)
    if not is_strict_json_value(value):
        raise _type_error(key, "JSON value", value)
    return value


def strict_row_json_object(row: Row, key: str) -> dict[str, JSONValue]:
    value = strict_row_json(row, key)
    if type(value) is not dict:
        raise _type_error(key, "JSON object", value)
    return value


def strict_row_optional[ValueT](
    row: Row,
    key: str,
    decoder: Callable[[Row, str], ValueT],
) -> ValueT | None:
    if key not in row or row[key] is None:
        return None
    return decoder(row, key)
