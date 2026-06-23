"""Logical audit column names for listener stamping."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditColumns:
    created: str = "created_on"
    updated: str = "updated_on"
    created_by: str = "created_by_id"
    updated_by: str = "updated_by_id"
    deleted: str = "deleted_on"
    deleted_by: str = "deleted_by_id"

    @classmethod
    def for_model(cls, model_type: type) -> AuditColumns:
        return cls()


def is_audit_model(instance: object) -> bool:
    from sqlphilosophy.audit.model import AuditMixin

    return isinstance(instance, AuditMixin)
