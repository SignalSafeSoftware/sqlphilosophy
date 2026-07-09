"""Trust-boundary helpers for developer-defined SQL fragments."""

from __future__ import annotations

import sqlphilosophy.trusted_sql as trusted_sql
from sqlphilosophy import sql
from sqlphilosophy.trusted_sql import col_eq, literal_order_expr, sql_table


def test_trusted_sql_module_docstring_warns_about_trust_boundary() -> None:
    assert trusted_sql.__doc__ is not None
    lowered = trusted_sql.__doc__.lower()
    assert "developer-defined" in lowered or "developer defined" in lowered
    assert "user" in lowered
    assert "bind" in lowered


def test_trusted_sql_public_api_is_explicit() -> None:
    assert "sql_table" in trusted_sql.__all__
    assert "literal_order_expr" in trusted_sql.__all__
    assert "col_eq" in trusted_sql.__all__


def test_sql_module_reexports_trusted_helpers_for_compatibility() -> None:
    assert sql.sql_table is sql_table
    assert sql.col_eq is col_eq
    assert sql.literal_order_expr is literal_order_expr


def test_trusted_sql_helpers_remain_callable_via_sql_import_path() -> None:
    tbl = sql.sql_table("demo", "id")
    assert tbl.name == "demo"
    expr, params = sql.col_eq("t.id", "id", 1)
    assert params == {"id": 1}
    assert expr is not None
    order = sql.literal_order_expr("demo.id DESC")
    assert order is not None
