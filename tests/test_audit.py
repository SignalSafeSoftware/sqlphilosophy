"""Audit context, listeners, and models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from conftest import SoftWidget, Widget
from sqlphilosophy.audit.context import (
    AuditContext,
    audit_context,
    get_audit_actor_id,
    get_audit_context,
    set_audit_context,
)
from sqlphilosophy.audit.fields import AuditColumns, is_audit_model
from sqlphilosophy.audit.listener import configure_audit_listeners, get_audit_listener, soft_delete


def test_audit_context_nested_and_reset() -> None:
    assert get_audit_actor_id() is None
    with audit_context(10):
        assert get_audit_actor_id() == 10
        with audit_context(20):
            assert get_audit_actor_id() == 20
        assert get_audit_actor_id() == 10
    assert get_audit_actor_id() is None


def test_audit_context_resets_on_exception() -> None:
    with pytest.raises(RuntimeError), audit_context(5):
        raise RuntimeError("boom")
    assert get_audit_actor_id() is None


def test_set_audit_context() -> None:
    set_audit_context(AuditContext(actor_id=7))
    assert get_audit_context() == AuditContext(actor_id=7)
    set_audit_context(None)
    assert get_audit_context() is None


def test_timestamp_model_stamps_on_insert(sync_session: Session) -> None:
    with audit_context(42):
        row = Widget(name="audited")
        sync_session.add(row)
        sync_session.flush()
    assert isinstance(row.created_on, datetime)
    assert isinstance(row.updated_on, datetime)
    assert row.created_by_id == 42
    assert row.updated_by_id == 42


def test_timestamp_model_stamps_on_update(sync_session: Session) -> None:
    row = Widget(name="before")
    sync_session.add(row)
    sync_session.flush()
    before = row.updated_on
    with audit_context(99):
        row.name = "after"
        sync_session.flush()
    assert row.updated_on >= before
    assert row.updated_by_id == 99


def test_soft_delete(sync_session: Session) -> None:
    row = SoftWidget(name="soft")
    sync_session.add(row)
    sync_session.flush()
    with audit_context(3):
        soft_delete(row)
    assert row.deleted_on is not None
    assert row.deleted_by_id == 3


def test_audit_columns_and_is_audit_model() -> None:
    cols = AuditColumns.for_model(Widget)
    assert cols.created == "created_on"
    assert is_audit_model(Widget(name="x")) is True
    assert is_audit_model(object()) is False


def test_configure_audit_listeners_idempotent() -> None:
    configure_audit_listeners()
    listener = get_audit_listener()
    listener.stamp_on_insert(Widget(name="direct"))
    assert listener.now().tzinfo is not None


def test_listener_set_helpers() -> None:
    listener = get_audit_listener()
    target = Widget(name="t")
    listener._set_if_empty(target, "created_on", listener.now())
    listener._set(target, "updated_by_id", 1)
    listener._set_if_empty(target, "missing_attr", 1)
    listener._set(object(), "anything", 1)


def test_listener_does_not_overwrite_nonempty_created_on() -> None:

    listener = get_audit_listener()
    row = Widget(name="filled")
    stamped = datetime.now(UTC)
    row.created_on = stamped
    listener._set_if_empty(row, "created_on", datetime.now(UTC))
    assert row.created_on == stamped
    listener.stamp_on_update(row)


def test_listener_stamps_update_without_actor(sync_session: Session) -> None:
    listener = get_audit_listener()
    row = Widget(name="no-actor")
    sync_session.add(row)
    sync_session.flush()
    before = row.updated_on
    listener.stamp_on_update(row)
    assert row.updated_on >= before


def test_listener_soft_delete_without_actor(sync_session: Session) -> None:
    listener = get_audit_listener()
    row = SoftWidget(name="soft-no-actor")
    sync_session.add(row)
    sync_session.flush()
    listener.stamp_on_soft_delete(row, actor=None)
    assert row.deleted_on is not None
    assert row.deleted_by_id is None
