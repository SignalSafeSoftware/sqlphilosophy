# Basic reads

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Use repository methods for simple equality filters and PK lookups. For richer queries, see [query-builder.md](./query-builder.md).

---

## `get_by_id` — nullable PK lookup

```python
# sync
user = user_repo.get_by_id(42)  # User | None

# async
user = await user_repo.get_by_id(42)
```

## `get` — required PK lookup

```python
# sync
try:
    user = user_repo.get(42)
except LookupError:
    ...  # no row for PK

# async
user = await user_repo.get(42)
```

## `get_many`

```python
# sync
users = user_repo.get_many([1, 2, 3])
assert user_repo.get_many([]) == []

# async
users = await user_repo.get_many([1, 2, 3])
```

## `exists` / `exists_where`

```python
# sync
if user_repo.exists(42):
    ...
if user_repo.exists_where(is_active=True, email="alice@example.com"):
    ...

# async
if await user_repo.exists(42):
    ...
if await user_repo.exists_where(is_active=True):
    ...
```

## `count`

```python
# sync
active = user_repo.count(is_active=True)
total = user_repo.count()

# async
active = await user_repo.count(is_active=True)
```

## `first`

```python
# sync
user = user_repo.first(email="alice@example.com")

# async
user = await user_repo.first(email="alice@example.com")
```

## `filter` — equality filters with optional pagination

```python
# sync — page=1, limit=20 → first 20 rows matching filters
page = user_repo.filter(page=1, limit=20, is_active=True)

# async
page = await user_repo.filter(page=1, limit=20, is_active=True)
```

## `get_all`

```python
# sync
all_users = user_repo.get_all()
first_page = user_repo.get_all(page=1, limit=50)

# async
all_users = await user_repo.get_all()
```

## `get_with_join` — explicit join tuples

```python
# sync — (User, Order) pairs for pending orders
pairs = user_repo.get_with_join(Order, Order.status == "pending", join_on=User.id == Order.user_id)

# async
pairs = await user_repo.get_with_join(Order, Order.status == "pending", join_on=User.id == Order.user_id)
```

## `load_relations` — eager loading

```python
from sqlalchemy.orm import selectinload

load = [selectinload(User.orders)]

# sync
user = user_repo.get(1, load_relations=load)
users = user_repo.filter(page=1, limit=10, load_relations=load, is_active=True)

# async
user = await user_repo.get(1, load_relations=load)
```

**Next:** [writes.md](./writes.md) · [query-builder.md](./query-builder.md)
