"""Portable SQLAlchemy repository typing aliases (PyPI-safe, no app imports)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy.engine import Result
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import ColumnElement, Select
from sqlalchemy.sql.selectable import FromClause, LateralFromClause, ScalarSelect, TableClause

__all__ = [
    "ApiObject",
    "ApiScalar",
    "IdList",
    "JSONObject",
    "JSONScalar",
    "JSONValue",
    "OrmModel",
    "PrimaryKey",
    "RowMapping",
    "RowValue",
    "SqlBindParams",
    "SqlClause",
    "SqlFilter",
    "SqlFilters",
    "SqlFromClause",
    "SqlLateral",
    "SqlOrderColumn",
    "SqlScalarSubquery",
    "SqlSelect",
    "SqlTable",
]

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]

type ApiScalar = JSONScalar | datetime | date | UUID
type RowValue = JSONScalar | datetime | date | UUID | bytes | dict[str, RowValue] | list[RowValue]
type ApiObject = dict[str, RowValue]

type PrimaryKey = int | str | UUID
type IdList = list[PrimaryKey]

type SqlBindParams = dict[str, RowValue]
type SqlClause = Any
type SqlFilter = ColumnElement[bool]
type SqlFilters = list[SqlFilter]
type SqlOrderColumn = ColumnElement[object]
type SqlSelect = Select[tuple[object, ...]]
type SqlFromClause = FromClause
type SqlLateral = LateralFromClause
type SqlScalarSubquery = ScalarSelect[object]
type SqlTable = TableClause

type RowMapping = Mapping[str, RowValue]

type OrmModel = type[DeclarativeBase]


def cursor_rowcount(result: Result[Any]) -> int:
    """Return affected row count from a DML ``execute`` result."""
    return int(cast(CursorResult[Any], result).rowcount or 0)
