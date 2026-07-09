# Audit helpers

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Audit **records changes**; it does **not** enforce authorization. Call `configure_audit_listeners()` once at startup.

---

## Audit model mixins

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from sqlphilosophy.audit.model import SoftDeleteTimestampModel, TimestampModel


class AuditedUser(TimestampModel):
    __tablename__ = "audited_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
```

Available mixins: `CreatedTimestampModel`, `UpdatedTimestampModel`, `TimestampModel`, `SoftDeleteTimestampModel`, `SoftDeleteModel`.

## Listeners and context

```python
from sqlphilosophy.audit.context import audit_context, get_audit_actor_id, get_audit_context
from sqlphilosophy.audit.fields import AuditColumns, is_audit_model
from sqlphilosophy.audit.listener import configure_audit_listeners, soft_delete

configure_audit_listeners()  # once at app startup
```

## Sync write with audit context

```python
from sqlphilosophy.sync.repository import BaseRepository

with SessionLocal() as session:
    repo = BaseRepository(AuditedUser, session)
    with audit_context(actor_id=current_user_id):
        user = repo.create(email="a@example.com")
        session.commit()
    assert get_audit_actor_id() is None  # outside context
```

## Async write with audit context

```python
from sqlphilosophy.aio.repository import AsyncBaseRepository

async with session_factory() as session:
    repo = AsyncBaseRepository(AuditedUser, session)
    with audit_context(actor_id=current_user_id):
        user = await repo.create(email="b@example.com")
        await session.commit()
```

## `soft_delete`, `AuditColumns`, `is_audit_model`

```python
with audit_context(actor_id=42):
    soft_delete(user_instance)  # stamps deleted_on / deleted_by_id on audit models
    session.commit()

fields = AuditColumns.for_model(AuditedUser)
assert is_audit_model(user_instance)
ctx = get_audit_context()
```

`update_partial` on audit models uses ORM setattr + flush so listeners can stamp audit columns. See [writes.md](./writes.md).

**Next:** [writes.md](./writes.md) · [types-version.md](./types-version.md)
