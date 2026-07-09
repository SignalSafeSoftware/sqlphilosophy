# Deletes

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

> **Dangerous operations** — authorize in application code before calling. This package does not enforce access control.

---

## `remove` — delete by PK

```python
# sync
deleted = user_repo.remove(user_id)  # bool; no commit
session.commit()

# async
deleted = await user_repo.remove(user_id)
await session.commit()
```

## `delete_many`

```python
# sync
count = user_repo.delete_many([1, 2, 3])
session.commit()

# async
count = await order_repo.delete_many([10, 11])
await session.commit()
```

## `delete_where` — criteria → PK lookup → bulk delete

```python
# sync
count = user_repo.delete_where(criteria=[User.is_active.is_(False)])
session.commit()

# async
count = await user_repo.delete_where(criteria=[User.email.like("%@spam.example")])
await session.commit()
```

## `delete_all` — delete every row for the model

> **Dangerous** — dev/ops only. Prefer scoped `delete_where` in application code.

```python
# sync
count = user_repo.delete_all()  # no commit
session.commit()

# async
count = await user_repo.delete_all()
await session.commit()
```

## `batched_purge_ids` — batched delete with per-batch commit

> **Dangerous** — deletes in chunks and **commits after each batch**. Requires `batch_size >= 1`. Use only after explicit authorization.

```python
# sync
if not app_user_can_purge(session, actor_id):
    raise PermissionError("not authorized")
total = user_repo.batched_purge_ids(
    criteria=[User.is_active.is_(False)],
    batch_size=500,
)
# each batch committed inside batched_purge_ids; session may have partial state

# async
total = await user_repo.batched_purge_ids(criteria=[Order.status == "cancelled"], batch_size=100)
```

`batch_size < 1` raises `ValueError("batch_size must be >= 1")`.

**Next:** [writes.md](./writes.md) · [mapping-helpers.md](./mapping-helpers.md)
