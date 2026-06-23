"""Sorting and pagination types."""

from __future__ import annotations
import pytest

from conftest import Widget
from sqlalchemy import desc
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sorting import SortConfig
from sqlphilosophy.sorting import SortSpec
from sqlphilosophy.sql import get_sort_column
from sqlphilosophy.sql import literal_order_expr


def test_list_query_from_page_valid() -> None:
    q = ListQuery.from_page(page=2, size=10, order_by={"name": "asc"})
    assert q.offset == 10
    assert q.limit == 10
    assert q.order_by == {"name": "asc"}


def test_list_query_from_page_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="page must be >= 1"):
        ListQuery.from_page(page=0, size=10)
    with pytest.raises(ValueError, match="size must be >= 1"):
        ListQuery.from_page(page=1, size=0)


def test_sort_config_allowlist_and_default() -> None:
    sort = SortConfig(
        default=SortSpec("id", "asc"),
        columns={"id": {"asc": Widget.id, "desc": Widget.id.desc()}, "name": {"asc": Widget.name}},
        allowlist=frozenset({"id"}),
    )
    assert sort.resolve_spec({"name": "asc"}) == SortSpec("id", "asc")
    assert sort.resolve_spec({"id": "desc"}) == SortSpec("id", "desc")


def test_sort_config_literal_sql_and_resolver() -> None:
    literal = SortConfig(
        default=SortSpec("id", "asc"),
        columns={"id": {"asc": "widget.id ASC", "desc": "widget.id DESC"}},
        literal_sql=True,
    )
    expr = get_sort_column(literal, {"id": "desc"})
    assert expr is not None

    def resolver(spec: SortSpec) -> tuple[object, object]:
        return (Widget.id, desc(Widget.name))

    custom = SortConfig(default=SortSpec("id", "asc"), resolver=resolver)
    clauses = custom.order_clauses(None)
    assert len(clauses) == 2


def test_sort_config_requires_columns_or_resolver() -> None:
    with pytest.raises(ValueError, match="requires columns or resolver"):
        SortConfig(default=SortSpec("id", "asc"))


def test_sort_config_literal_sql_requires_string() -> None:
    bad = SortConfig(
        default=SortSpec("id", "asc"),
        columns={"id": {"asc": Widget.id, "desc": Widget.id.desc()}},
        literal_sql=True,
    )
    with pytest.raises(TypeError, match="literal_sql"):
        bad.order_expression({"id": "asc"})


def test_literal_order_expr_desc() -> None:
    assert literal_order_expr("widget.name DESC") is not None
    assert literal_order_expr("widget.name") is not None
