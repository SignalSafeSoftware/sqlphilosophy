"""Sorting and pagination types."""

from __future__ import annotations

import pytest
from sqlalchemy import desc

from conftest import Widget
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sql import get_sort_column, literal_order_expr


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


def test_sort_config_valid_sort_resolves_correctly() -> None:
    sort = SortConfig(
        default=SortSpec("id", "asc"),
        columns={
            "id": {"asc": Widget.id, "desc": Widget.id.desc()},
            "name": {"asc": Widget.name, "desc": Widget.name.desc()},
        },
    )
    assert sort.resolve_spec({"name": "desc"}) == SortSpec("name", "desc")


def test_sort_config_missing_sort_uses_default() -> None:
    default = SortSpec("id", "asc")
    sort = SortConfig(
        default=default,
        columns={"id": {"asc": Widget.id, "desc": Widget.id.desc()}},
    )
    assert sort.resolve_spec(None) == default
    assert sort.resolve_spec({}) == default


def test_sort_config_invalid_sort_falls_back_with_default_policy() -> None:
    default = SortSpec("id", "asc")
    sort = SortConfig(
        default=default,
        columns={"id": {"asc": Widget.id, "desc": Widget.id.desc()}},
        allowlist=frozenset({"id"}),
        invalid="default",
    )
    assert sort.resolve_spec({"unknown": "asc"}) == default
    assert sort.resolve_spec({"id": "sideways"}) == default


def test_sort_config_invalid_sort_raises_with_strict_policy() -> None:
    sort = SortConfig(
        default=SortSpec("id", "asc"),
        columns={"id": {"asc": Widget.id, "desc": Widget.id.desc()}},
        allowlist=frozenset({"id"}),
        invalid="raise",
    )
    with pytest.raises(ValueError, match="invalid sort column: 'unknown'"):
        sort.resolve_spec({"unknown": "asc"})
    with pytest.raises(ValueError, match="invalid sort direction: 'sideways'"):
        sort.resolve_spec({"id": "sideways"})


def test_sort_config_rejects_unknown_invalid_policy() -> None:
    with pytest.raises(ValueError, match='invalid must be "default" or "raise"'):
        SortConfig(
            default=SortSpec("id", "asc"),
            columns={"id": {"asc": Widget.id}},
            invalid="ignore",  # type: ignore[arg-type]
        )


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
