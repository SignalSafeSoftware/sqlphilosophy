# Writes and updates

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Covers creates, staging, partial updates, bulk updates, and transaction ownership.

---

## Basic writes

### `create` and `add`

```python
# sync
user = user_repo.create(email="c@example.com", display_name="Carol")  # flush
# or stage a pre-built instance:
user = User(email="d@example.com", display_name="Dan")
user_repo.add(user)

session.commit()

# async
user = await user_repo.create(email="c@example.com", display_name="Carol")
await session.commit()
```

### `get_or_create`

```python
# sync
user, created = user_repo.get_or_create(
    defaults={"display_name": "Eve"},
    email="eve@example.com",
)
if created:
    session.commit()  # only needed when a row was inserted

# async
user, created = await user_repo.get_or_create(defaults={"display_name": "Eve"}, email="eve@example.com")
if created:
    await session.commit()
```

### Commit ownership and rollback

```python
# sync
try:
    user_repo.create(email="bad@", display_name="X")  # may fail validation at DB layer
    order_repo.create(user_id=999, total=10.0)        # FK failure
    session.commit()
except Exception:
    session.rollback()
    raise

# async
try:
    await user_repo.create(email="bad@", display_name="X")
    await session.commit()
except Exception:
    await session.rollback()
    raise
```

---

## Updates

### `update_partial` with writable allowlist

```python
WRITABLE = frozenset({"display_name", "is_active"})

# sync
rows = user_repo.update_partial(
    user_id,
    {"display_name": "Alice Updated", "is_active": False},
    WRITABLE,
)
session.commit()  # caller commits after DML/flush

# async
rows = await user_repo.update_partial(user_id, {"display_name": "Alice Updated"}, WRITABLE)
await session.commit()
```

Keys not in `writable` are ignored. Returns affected row count (`0` when PK missing or nothing to apply).

### `touch_updated_on`

For models with an `updated_on` column, pass `touch_updated_on=True` to stamp the timestamp during partial update.

```python
user_repo.update_partial(user_id, {"display_name": "New"}, WRITABLE, touch_updated_on=True)
```

### `update_where` — bulk UPDATE

```python
# sync
count = user_repo.update_where(
    criteria=[User.is_active.is_(False)],
    values={"display_name": "Inactive user"},
)
assert count >= 0
session.commit()

# async
count = await user_repo.update_where(criteria=[User.is_active.is_(False)], values={"display_name": "Inactive user"})
await session.commit()
```

### Empty update values return `0`

```python
assert user_repo.update_where(criteria=[User.id == 1], values={}) == 0
```

### Audit model behavior

Models mixing in `TimestampModel` (or other audit mixins) use the **ORM setattr path** during `update_partial`: load instance, apply allowed fields, **flush** — still **no commit**. Audit listeners stamp `created_by_id` / `updated_by_id` when `audit_context` is active. See [audit.md](./audit.md).

**Next:** [deletes.md](./deletes.md) · [audit.md](./audit.md)
