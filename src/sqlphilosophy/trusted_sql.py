"""Developer-trusted SQL fragments and Core table helpers.

Use this module when building SQLAlchemy Core expressions from **developer-defined**
identifiers and SQL text. Every string parameter that names a table, column, or
``ORDER BY`` fragment must come from application code (constants, allowlists, or
ORM metadata)—**never** from end-user input.

User-supplied **values** belong in bind parameters (see ``col_eq``, ``col_icontains``,
``col_range``). Do not concatenate user input into identifiers or raw SQL fragments.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from sqlalchemy import bindparam, desc, func, literal_column
from sqlalchemy.sql import column, table

from sqlphilosophy.types import ApiObject, RowValue, SqlFilter, SqlOrderColumn, SqlTable

__all__ = (
    "col_eq",
    "col_icontains",
    "col_range",
    "literal_order_expr",
    "order_by_allowlist",
    "order_expr_from_sort",
    "sql_table",
)


def sql_table(table_name: str, *column_names: str) -> SqlTable:
    """Build a Core ``table()`` from developer-defined table and column names.

    ``table_name`` and each entry in ``column_names`` must be trusted identifiers
    defined in application code—not derived from request parameters or other
    user-controlled input.
    """
    return table(table_name, *[column(c) for c in column_names])


def col_eq(col_sql: str, param_name: str, value: object) -> tuple[SqlFilter, ApiObject]:
    """Equality filter: ``col_sql`` is a trusted column SQL fragment; ``value`` is bound."""
    return literal_column(col_sql) == bindparam(param_name), cast(ApiObject, {param_name: cast(RowValue, value)})


def col_icontains(
    col_sql: str,
    param_name: str,
    raw: object,
) -> tuple[SqlFilter, ApiObject] | None:
    """Case-insensitive ``LIKE`` filter; ``col_sql`` is trusted, search text is bound."""
    text_value = str(raw).strip()
    if not text_value:
        return None
    crit = func.lower(literal_column(col_sql)).like(bindparam(param_name))
    return crit, {param_name: f"%{text_value.lower()}%"}


def col_range(
    col_sql: str,
    param_name: str,
    operator: str,
    value: object,
) -> tuple[SqlFilter, ApiObject]:
    """Range filter (``>=`` or ``<=``); ``col_sql`` is trusted, ``value`` is bound."""
    col: SqlOrderColumn = literal_column(col_sql)
    if operator == ">=":
        return col >= bindparam(param_name), cast(ApiObject, {param_name: cast(RowValue, value)})
    if operator == "<=":
        return col <= bindparam(param_name), cast(ApiObject, {param_name: cast(RowValue, value)})
    raise ValueError(f"unsupported operator: {operator}")


def order_by_allowlist(
    order_key: str,
    ordering_map: Mapping[str, str],
    *,
    allowlist: frozenset[str],
) -> SqlOrderColumn:
    """Resolve ``order_key`` through an allowlist to a trusted ``ORDER BY`` fragment."""
    if order_key not in allowlist:
        raise ValueError(f"invalid order key: {order_key}")
    return literal_order_expr(ordering_map[order_key])


def literal_order_expr(spec: str) -> SqlOrderColumn:
    """Build ``ORDER BY`` from a developer-defined SQL fragment such as ``a.started_at DESC``.

    ``spec`` must be a trusted fragment from application code—never built from user input.
    """
    parts = spec.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].upper() == "DESC":
        return desc(literal_column(parts[0]))
    return literal_column(spec)


def order_expr_from_sort(
    column: str,
    direction: str,
    *,
    columns: Mapping[str, Mapping[str, str]],
) -> SqlOrderColumn:
    """Build ``ORDER BY`` from sort metadata; column specs must be developer-defined strings."""
    return literal_order_expr(columns[column][direction])
