"""SQLAlchemy audit listeners gated on :class:`AuditMixin`."""

from __future__ import annotations
from abc import ABC
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast
from sqlalchemy import event
from sqlalchemy.orm import Mapper
from sqlphilosophy.audit.context import get_audit_context
from sqlphilosophy.audit.fields import AuditColumns
from sqlphilosophy.audit.fields import is_audit_model
from sqlphilosophy.audit.model import AuditMixin

_ATTACHED = False


class AuditListener(ABC):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _actor(self) -> int | str | None:
        ctx = get_audit_context()
        return ctx.actor_id if ctx is not None else None

    def _has_attr(self, target: object, name: str) -> bool:
        return hasattr(type(target), name)

    def _set_if_empty(self, target: object, name: str, value: object) -> None:
        if not self._has_attr(target, name):
            return
        current = getattr(target, name)
        if current is None or current == "":
            setattr(target, name, value)

    def _set(self, target: object, name: str, value: object) -> None:
        if self._has_attr(target, name):
            setattr(target, name, value)

    def stamp_on_insert(self, target: AuditMixin) -> None:
        fields = AuditColumns.for_model(type(target))
        ts = self.now()
        self._set_if_empty(target, fields.created, ts)
        self._set_if_empty(target, fields.updated, ts)
        actor = self._actor()
        if actor is not None:
            self._set_if_empty(target, fields.created_by, actor)
            self._set_if_empty(target, fields.updated_by, actor)

    def stamp_on_update(self, target: AuditMixin) -> None:
        fields = AuditColumns.for_model(type(target))
        if self._has_attr(target, fields.updated):
            setattr(target, fields.updated, self.now())
        actor = self._actor()
        if actor is not None:
            self._set(target, fields.updated_by, actor)

    def stamp_on_soft_delete(self, target: AuditMixin, *, actor: int | str | None = None) -> None:
        fields = AuditColumns.for_model(type(target))
        self._set(target, fields.deleted, self.now())
        resolved = actor if actor is not None else self._actor()
        if resolved is not None:
            self._set(target, fields.deleted_by, resolved)

    def attach(self) -> None:
        global _ATTACHED
        if _ATTACHED:
            return
        listener = self

        @event.listens_for(AuditMixin, "before_insert", propagate=True)
        def _before_insert(mapper: Mapper[Any], connection: object, target: object) -> None:
            if not is_audit_model(target):
                return  # pragma: no cover
            listener.stamp_on_insert(cast(AuditMixin, target))

        @event.listens_for(AuditMixin, "before_update", propagate=True)
        def _before_update(mapper: Mapper[Any], connection: object, target: object) -> None:
            if not is_audit_model(target):
                return  # pragma: no cover
            listener.stamp_on_update(cast(AuditMixin, target))

        _ATTACHED = True


_default_listener = AuditListener()


def get_audit_listener() -> AuditListener:
    return _default_listener


def configure_audit_listeners() -> None:
    _default_listener.attach()


def soft_delete(target: AuditMixin, *, actor: int | str | None = None) -> None:
    """Stamp soft-delete columns via the configured audit listener."""
    get_audit_listener().stamp_on_soft_delete(target, actor=actor)
