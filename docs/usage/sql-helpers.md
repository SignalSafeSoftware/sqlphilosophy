# SQL helpers

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Module: `sqlphilosophy.sql` — **sync `Session` helpers** (and pure functions). Async apps typically call these from sync code paths or use repository async methods for the same workflows.

Use from a service function that holds `session: Session`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlphilosophy.sql import (
    api_float,
    api_int,
    apply_mappings_page,
    apply_writable_update,
    combine_and,
    count_composed_select,
    count_from_subquery,
    count_from_table,
    delete_by_ids,
    delete_by_ids_model,
    expanding_in_param,
    get_sort_column,
    merge_criteria,
    partial_update,
    partial_update_model,
    row_bool,
    row_float,
    row_int,
    row_json,
    row_mapping,
    row_str,
    row_uuid,
    rows_mapping,
    select_page_from_table,
)
from sqlphilosophy.trusted_sql import sql_table
```

---

## Row mapping and typed accessors

```python
result = session.execute(select(User.id, User.email, User.is_active)).mappings().first()
row = row_mapping(result)
email = row_str(row, "email")
active = row_bool(row, "is_active")
user_id = row_int(row, "id")
# also: row_float, row_json, row_uuid, row_opt_* variants

all_rows = rows_mapping(session.execute(stmt).mappings().all())
```

## API dict accessors

```python
payload = {"count": "3", "rate": "1.5"}
n = api_int(payload, "count", default=0)
rate = api_float(payload, "rate", default=0.0)
```

## Partial updates

```python
WRITABLE = frozenset({"display_name"})

# ORM model path (same logic as repo.update_partial)
partial_update_model(session, User, pk_value, {"display_name": "X"}, WRITABLE, touch_updated_on=True)

# Core table path — table_name is a trusted identifier
tbl = sql_table("user", "id", "display_name")
partial_update(session, "user", pk_value, {"display_name": "X"}, WRITABLE)

# in-memory merge before flush
apply_writable_update(user_instance, {"display_name": "X"}, WRITABLE)
```

See [writes.md](./writes.md) for repository-level partial updates.

## Deletes and criteria

```python
delete_by_ids_model(session, User, [1, 2, 3])
delete_by_ids(session, tbl, [1, 2, 3])

crit_a = User.is_active.is_(True)
crit_b = User.email.like("%@example.com")
merged = merge_criteria([crit_a, crit_b])
combined = combine_and(crit_a, crit_b)
```

## Count and pagination helpers

```python
base = select(User).where(User.is_active.is_(True))
count_stmt = count_composed_select(base)
total = session.scalar(count_stmt)

subq = base.subquery()
total = count_from_subquery(session, subq)

total = count_from_table(session, User, criteria=[User.is_active.is_(True)])

page_rows = select_page_from_table(session, User, limit=20, offset=0, criteria=[User.is_active.is_(True)])
page_rows = apply_mappings_page(session, select(User.id, User.email), limit=20, offset=0)
```

## Sort column and expanding IN

```python
col = get_sort_column(User, "email")
param, binds = expanding_in_param("ids", [1, 2, 3])
stmt = select(User).where(User.id.in_(param)).params(**binds)
```

**Next:** [trusted-sql.md](./trusted-sql.md) · [mapping-helpers.md](./mapping-helpers.md)
