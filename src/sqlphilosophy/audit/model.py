"""Abstract mixins that gate audit listener processing."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """Base marker for audit listener dispatch."""

    __abstract__ = True


class CreatedTimestampModel(AuditMixin):
    """Tables with ``created_on`` only (outbox, audit events, invites)."""

    __abstract__ = True

    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UpdatedTimestampModel(AuditMixin):
    """Tables with ``updated_on`` only."""

    __abstract__ = True

    updated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TimestampModel(AuditMixin):
    """Standard created/updated timestamp and actor audit columns."""

    __abstract__ = True

    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class SoftDeleteTimestampModel(TimestampModel):
    """Timestamped entities that support soft delete."""

    __abstract__ = True

    deleted_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class SoftDeleteModel(AuditMixin):
    """Soft-delete columns without created/updated timestamps (e.g. Profile)."""

    __abstract__ = True

    deleted_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
