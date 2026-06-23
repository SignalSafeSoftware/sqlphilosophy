"""List pagination and sort resolution for repository queries."""

from __future__ import annotations
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

SortDirection = Literal["asc", "desc"]
OrderByMap = dict[str, SortDirection]


@dataclass(frozen=True)
class SortSpec:
    column: str
    direction: SortDirection


@dataclass(frozen=True)
class ListQuery:
    """Offset/limit slice plus optional client sort (first ``order_by`` entry wins)."""

    offset: int
    limit: int
    order_by: OrderByMap | None = None

    @classmethod
    def from_page(
        cls,
        *,
        page: int,
        size: int,
        order_by: OrderByMap | None = None,
    ) -> ListQuery:
        if page < 1:
            raise ValueError("page must be >= 1")
        if size < 1:
            raise ValueError("size must be >= 1")
        return cls(offset=(page - 1) * size, limit=size, order_by=order_by)


SortResolver = Callable[[SortSpec], object]


class SortConfig:
    """Allowed sort columns for a list endpoint.

    Provide either:

    * ``columns`` — map of API column name → ``{asc, desc}`` SQL/ORM expressions, or
    * ``columns`` + ``literal_sql=True`` — map of string SQL fragments, or
    * ``resolver`` — custom ``SortSpec → order clause(s)`` function.
    """

    def __init__(
        self,
        *,
        default: SortSpec,
        columns: Mapping[str, Mapping[str, object]] | None = None,
        allowlist: frozenset[str] | None = None,
        literal_sql: bool = False,
        resolver: SortResolver | None = None,
    ) -> None:
        if resolver is None and columns is None:
            raise ValueError("SortConfig requires columns or resolver")
        self._default = default
        self._columns = columns or {}
        self._literal_sql = literal_sql
        self._resolver = resolver
        self._allowlist = allowlist if allowlist is not None else frozenset(self._columns)

    def resolve_spec(self, order_by: OrderByMap | None) -> SortSpec:
        if order_by:
            column, direction = next(iter(order_by.items()))
            if direction in ("asc", "desc") and column in self._allowlist:
                return SortSpec(column, direction)
        return self._default

    def order_expression(self, order_by: OrderByMap | None) -> object:
        """Return a single ORDER BY expression or a tuple of clauses."""
        spec = self.resolve_spec(order_by)
        if self._resolver is not None:
            return self._resolver(spec)
        if self._literal_sql:
            from sqlphilosophy.sql import literal_order_expr

            raw = self._columns[spec.column][spec.direction]
            if not isinstance(raw, str):
                raise TypeError("literal_sql SortConfig requires string column specs")
            return literal_order_expr(raw)
        return self._columns[spec.column][spec.direction]

    def order_clauses(self, order_by: OrderByMap | None) -> tuple[object, ...]:
        expr = self.order_expression(order_by)
        if isinstance(expr, tuple):
            return expr
        return (expr,)
