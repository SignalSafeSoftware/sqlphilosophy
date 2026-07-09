# Fluent query builder

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Entry point: `repo.statement()` (or `SqlAlchemyStatementBuilder` / `AsyncSqlAlchemyStatementBuilder` with session + model).

```python
builder = user_repo.statement()
```

Builder methods return a **new builder** (immutable-style chaining). Terminal methods execute the query.

---

## Composition methods

```python
from sqlalchemy import func

# sync — filter, project, join
rows = (
    user_repo.statement()
    .select_columns(User.id, User.email, func.count(Order.id).label("n"))
    .join(Order, User.id == Order.user_id)
    .where(User.is_active.is_(True))
    .group_by(User.id, User.email)
    .order_by(User.email.asc())
    .limit(10)
    .mappings()
    .all()
)

# async
rows = await (
    user_repo.statement()
    .where(User.is_active.is_(True))
    .filter_by(is_active=True)  # equality shorthand
    .mappings()
    .all()
)
```

| Method | Purpose |
|--------|---------|
| `.select_entity()` | SELECT ORM entity (default) |
| `.select_table()` | Table-only projection |
| `.select_columns(*cols)` | Explicit column list |
| `.select_from(clause)` | Custom FROM |
| `.join` / `.outerjoin` | Join targets |
| `.where(*criteria)` | SQLAlchemy boolean criteria |
| `.filter_by(**kwargs)` | Equality filters |
| `.distinct()` | Portable row-level DISTINCT |
| `.distinct(User.email)` | PostgreSQL DISTINCT ON (not portable) |
| `.group_by(*clauses)` | GROUP BY |
| `.correlate(*froms)` / `.correlate_except(*froms)` | Subquery correlation |
| `.as_lateral(name)` / `.as_cte(name)` | Lateral / CTE clause objects |
| `.order_by(*clauses)` | Raw ORDER BY |
| `.apply_sort(sort, order_by=None)` | Client sort via `SortConfig` |
| `.limit(n)` / `.offset(n)` | Pagination (`>= 0`) |
| `.with_params(params)` | Bind parameters |
| `.with_for_update(of=None, skip_locked=False)` | Row lock (dialect-dependent) |
| `.build_select()` | Inspect composed SELECT only |

### `distinct` — portable vs PostgreSQL

```python
# portable — all selected columns
user_repo.statement().distinct().mappings().all()

# PostgreSQL DISTINCT ON — not portable
user_repo.statement().distinct(User.email).order_by(User.email).mappings().all()
```

### Lateral / CTE

```python
# sync — builder instance methods
sub = user_repo.statement().select_columns(User.id).where(User.is_active.is_(True))
lateral = sub.as_lateral("active_users")
cte = sub.as_cte("active_users")

# sync-only module helpers (same semantics):
from sqlphilosophy.sync.query import cte_from, lateral_from

cte = cte_from(sub.build_select(), "active_users")
```

Async builders support `.as_lateral()` / `.as_cte()` on the instance.

### `with_for_update`

```python
# sync — dialect-dependent row lock
user_repo.statement().where(User.id == 1).with_for_update().scalars().first()

# async
await user_repo.statement().where(User.id == 1).with_for_update(skip_locked=True).scalars().first()
```

### `build_select` — debug only

```python
stmt = user_repo.statement().where(User.is_active.is_(True)).build_select()
# log str(stmt) — execute via terminal methods, not raw session.execute(stmt) unless intentional
```

---

## Terminal methods

Terminals **execute** the composed query.

### Mappings

```python
# sync
all_rows = user_repo.statement().where(User.is_active.is_(True)).mappings().all()
first_row = user_repo.statement().filter_by(email="a@example.com").mappings().first()
one_row = user_repo.statement().where(User.id == 1).mappings().one()

# async
all_rows = await user_repo.statement().mappings().all()
first_row = await user_repo.statement().mappings().first()
```

### Scalars (ORM entities)

```python
# sync
users = user_repo.statement().where(User.is_active.is_(True)).scalars().all()
user = user_repo.statement().filter_by(email="a@example.com").scalars().first()

# async
users = await user_repo.statement().scalars().all()
```

### `scalar` / `scalar_one`

```python
# sync
email = user_repo.statement().select_columns(User.email).where(User.id == 1).scalar()
email = user_repo.statement().select_columns(User.email).where(User.id == 1).scalar_one()

# async
email = await user_repo.statement().select_columns(User.email).where(User.id == 1).scalar()
```

### `count` / `count_distinct`

```python
# sync — ignores limit/offset/order on inner query
total = user_repo.statement().where(User.is_active.is_(True)).count()
distinct_emails = user_repo.statement().count_distinct(User.email)

# async
total = await user_repo.statement().where(User.is_active.is_(True)).count()
```

### `fetch_page` — returns `(rows, total)` tuple

**Does not mutate the builder** — copies internally, applies sort, counts, then fetches one page.

```python
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec

sort = SortConfig(
    default=SortSpec("email", "asc"),
    columns={"email": {"asc": User.email, "desc": User.email.desc()}},
)
list_query = ListQuery.from_page(page=2, size=20)

# sync
rows, total = user_repo.statement().where(User.is_active.is_(True)).fetch_page(list_query, sort=sort)

# async
rows, total = await user_repo.statement().fetch_page(list_query, sort=sort)
```

Unpack as `rows, total = ...` — there is no `page.total` object. See [sorting-pagination.md](./sorting-pagination.md).

**Next:** [sorting-pagination.md](./sorting-pagination.md) · [mapping-helpers.md](./mapping-helpers.md)
