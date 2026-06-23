"""Audit context, listeners, and models."""

from __future__ import annotations
from datetime import datetime
import pytest

from conftest import SoftWidget
from conftest import Widget
from sqlalchemy.orm import Session
from sqlphilosophy.audit.context import audit_context
from sqlphilosophy.audit.context import AuditContext
from sqlphilosophy.audit.context import get_audit_actor_id
from sqlphilosophy.audit.context import get_audit_context
from sqlphilosophy.audit.context import set_audit_context
from sqlphilosophy.audit.fields import AuditColumns
from sqlphilosophy.audit.fields import is_audit_model
from sqlphilosophy.audit.listener import configure_audit_listeners
from sqlphilosophy.audit.listener import get_audit_listener
from sqlphilosophy.audit.listener import soft_delete


def test_audit_context_nested_and_reset() -> None:
    assert get_audit_actor_id() is None
    with audit_context(10):
        assert get_audit_actor_id() == 10
        with audit_context(20):
            assert get_audit_actor_id() == 20
        assert get_audit_actor_id() == 10
    assert get_audit_actor_id() is None


def test_audit_context_resets_on_exception() -> None:
    with pytest.raises(RuntimeError):
        with audit_context(5):
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
