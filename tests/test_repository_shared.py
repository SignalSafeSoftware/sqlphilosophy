"""Unit tests for internal repository policy helpers."""

from __future__ import annotations

import pytest

from conftest import Tag, Widget
from sqlphilosophy._repository_shared import (
    PartialUpdatePlan,
    bulk_update_allowed,
    criteria_delete_allowed,
    extract_primary_keys,
    filter_writable_updates,
    lookup_not_found_message,
    plan_partial_update,
    require_batch_size,
    require_mappings_page_limits,
    require_page_and_limit,
)


def test_filter_writable_updates() -> None:
    assert filter_writable_updates({"a": 1, "b": 2}, frozenset({"a"})) == {"a": 1}


def test_plan_partial_update_audit_skip_when_no_writable_fields() -> None:
    plan = plan_partial_update(Widget, {"name": "x"}, frozenset())
    assert plan.action == "skip"


def test_plan_partial_update_audit_applies_extra_values() -> None:
    plan = plan_partial_update(
        Widget,
        {"name": "x"},
        frozenset({"name"}),
        extra_values={"active": False},
    )
    assert plan.action == "audit"
    assert plan.updates == {"name": "x", "active": False}


def test_plan_partial_update_core_touch_updated_on() -> None:
    plan = plan_partial_update(
        Tag,
        {"label": "x"},
        frozenset({"label"}),
        touch_updated_on=True,
    )
    assert plan.action == "core"
    assert plan.updates is not None
    assert "updated_on" in plan.updates


def test_partial_update_plan_updates_for_action_mismatch() -> None:
    plan = PartialUpdatePlan("audit", {"name": "x"})
    with pytest.raises(RuntimeError, match="action mismatch"):
        plan.updates_for("core")


def test_partial_update_plan_updates_for_missing_payload() -> None:
    plan = PartialUpdatePlan("core")
    with pytest.raises(RuntimeError, match="missing updates payload"):
        plan.updates_for("core")


def test_extract_primary_keys() -> None:
    rows = [{"id": 1}, {"id": 2}]
    assert extract_primary_keys(rows, "id") == [1, 2]


def test_lookup_not_found_message() -> None:
    assert lookup_not_found_message(Widget, 42) == "Widget matching id=42 not found"


@pytest.mark.parametrize("batch_size", [0, -3])
def test_require_batch_size(batch_size: int) -> None:
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        require_batch_size(batch_size)


def test_require_page_and_limit() -> None:
    with pytest.raises(ValueError, match="page must be >= 1"):
        require_page_and_limit(page=0, limit=None)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        require_page_and_limit(page=1, limit=0)


def test_require_mappings_page_limits() -> None:
    with pytest.raises(ValueError, match="limit must be >= 0"):
        require_mappings_page_limits(limit=-1, offset=0)
    with pytest.raises(ValueError, match="offset must be >= 0"):
        require_mappings_page_limits(limit=0, offset=-1)


def test_criteria_and_bulk_guards() -> None:
    assert criteria_delete_allowed([]) is False
    assert bulk_update_allowed({}) is False
    assert criteria_delete_allowed([object()]) is True
    assert bulk_update_allowed({"name": "x"}) is True
