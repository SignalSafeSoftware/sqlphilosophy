"""Internal helpers shared by sync and async repository implementations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase

from sqlphilosophy.audit.model import AuditMixin
from sqlphilosophy.types import PrimaryKey, RowMapping, RowValue, SqlFilter


def require_batch_size(batch_size: int) -> None:
    """Validate batch size for destructive batched repository operations."""
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")


def require_single_column_primary_key(model: type[DeclarativeBase], mapper: Any) -> Any:
    """Return the sole primary-key column or raise when the mapper is invalid."""
    pk_cols = mapper.primary_key
    if len(pk_cols) != 1:
        raise TypeError(f"{model.__name__} must have a single-column primary key")
    return pk_cols[0]


def require_page_and_limit(*, page: int, limit: int | None) -> None:
    """Validate repository pagination inputs."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")


def require_mappings_page_limits(*, limit: int, offset: int) -> None:
    """Validate limit/offset for mapping page fetches."""
    if limit < 0:
        raise ValueError("limit must be >= 0")
    if offset < 0:
        raise ValueError("offset must be >= 0")


def filter_writable_updates(fields: RowMapping, writable: frozenset[str]) -> RowMapping:
    """Keep only keys allowed by ``writable``."""
    return {k: v for k, v in fields.items() if k in writable}


def lookup_not_found_message(model: type[DeclarativeBase], obj_id: PrimaryKey) -> str:
    """Message for ``LookupError`` when a primary-key fetch misses."""
    return f"{model.__name__} matching id={obj_id!r} not found"


def extract_primary_keys(rows: Sequence[RowMapping], pk_key: str) -> list[PrimaryKey]:
    """Collect primary-key values from statement mapping rows."""
    return [cast(PrimaryKey, row[pk_key]) for row in rows]


@dataclass(frozen=True)
class PartialUpdatePlan:
    """Prepared partial-update action for sync or async execution."""

    action: Literal["skip", "audit", "core"]
    updates: RowMapping | None = None

    def updates_for(self, action: Literal["audit", "core"]) -> RowMapping:
        """Return the updates payload for an audit or core plan."""
        if self.action != action:
            raise RuntimeError(f"partial update plan action mismatch: expected {action!r}, got {self.action!r}")
        if self.updates is None:
            raise RuntimeError(f"partial update plan {action!r} is missing updates payload")
        return self.updates


def plan_partial_update(
    model: type[DeclarativeBase],
    fields: RowMapping,
    writable: frozenset[str],
    *,
    touch_updated_on: bool = False,
    extra_values: RowMapping | None = None,
) -> PartialUpdatePlan:
    """Prepare audit ORM, core UPDATE, or no-op partial update payloads."""
    if issubclass(model, AuditMixin):
        audit_updates = filter_writable_updates(fields, writable)
        if extra_values:
            audit_updates = {**audit_updates, **extra_values}
        if not audit_updates:
            return PartialUpdatePlan("skip")
        return PartialUpdatePlan("audit", audit_updates)

    core_updates = filter_writable_updates(fields, writable)
    if extra_values:
        core_updates = {**core_updates, **extra_values}
    if not core_updates:
        return PartialUpdatePlan("skip")
    if touch_updated_on:
        core_updates = cast(
            RowMapping,
            {**dict(core_updates), "updated_on": cast(RowValue, func.now())},
        )
    return PartialUpdatePlan("core", core_updates)


def criteria_delete_allowed(criteria: Sequence[SqlFilter]) -> bool:
    """True when ``delete_where`` should run a lookup before deleting."""
    return bool(criteria)


def bulk_update_allowed(values: RowMapping) -> bool:
    """True when ``update_where`` has values to apply."""
    return bool(values)
