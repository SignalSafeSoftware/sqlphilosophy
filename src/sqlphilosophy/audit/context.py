"""Request-scoped audit actor context."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditContext:
    actor_id: int | str | None = None


_audit_context: ContextVar[AuditContext | None] = ContextVar("audit_context", default=None)


def get_audit_context() -> AuditContext | None:
    return _audit_context.get()


def get_audit_actor_id() -> int | str | None:
    ctx = get_audit_context()
    return ctx.actor_id if ctx is not None else None


def set_audit_context(ctx: AuditContext | None) -> None:
    _audit_context.set(ctx)


@contextmanager
def audit_context(actor_id: int | str | None) -> Iterator[None]:
    token = _audit_context.set(AuditContext(actor_id=actor_id))
    try:
        yield
    finally:
        _audit_context.reset(token)
