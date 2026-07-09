# Mapping helpers

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Use mapping helpers when you need **dict rows** from Core/ORM `select()` statements instead of entity instances — reports, exports, or hand-built SQL.

```python
from sqlalchemy import func, select

stmt = select(User.id, User.email, func.count(Order.id).label("order_count")).join(Order).group_by(User.id)
```

---

## `fetch_statement_mappings`

```python
# sync
rows = user_repo.fetch_statement_mappings(stmt)

# async
rows = await user_repo.fetch_statement_mappings(stmt)
```

## `iter_mappings`

```python
# sync
for row in user_repo.iter_mappings(stmt):
    process(row)

# async
async for row in user_repo.iter_mappings(stmt):
    process(row)
```

## `fetch_mapping_first` / `fetch_mapping_one`

```python
# sync
first = user_repo.fetch_mapping_first(stmt)
exactly_one = user_repo.fetch_mapping_one(select(User.id).where(User.id == 1))

# async
first = await user_repo.fetch_mapping_first(stmt)
```

## `fetch_mappings_page`

```python
# sync
page = user_repo.fetch_mappings_page(stmt, limit=20, offset=0)

# async
page = await user_repo.fetch_mappings_page(stmt, limit=20, offset=40)
```

## `fetch_sorted_mappings`

```python
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec

sort = SortConfig(default=SortSpec("email", "asc"), columns={"email": {"asc": User.email, "desc": User.email.desc()}})
list_query = ListQuery.from_page(page=1, size=20, order_by={"email": "asc"})

# sync
rows = user_repo.fetch_sorted_mappings(stmt, list_query=list_query, sort=sort)

# async
rows = await user_repo.fetch_sorted_mappings(stmt, list_query=list_query, sort=sort)
```

See [sorting-pagination.md](./sorting-pagination.md) for `ListQuery` and `SortConfig` details.

## `scalar_count`

```python
count_stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))

# sync
n = user_repo.scalar_count(count_stmt)

# async
n = await user_repo.scalar_count(count_stmt)
```

**When to use ORM methods instead:** use `get`, `filter`, and builder `.scalars()` when you want mapped entity instances with relationships and unit-of-work tracking. See [reads.md](./reads.md) and [query-builder.md](./query-builder.md).

**Next:** [query-builder.md](./query-builder.md) · [sorting-pagination.md](./sorting-pagination.md)
