# Trusted SQL helpers

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Module: **`sqlphilosophy.trusted_sql`** (re-exported from `sqlphilosophy.sql`).

---

## Trust boundary

| Safe | Unsafe |
|------|--------|
| Table/column names from constants, ORM metadata, allowlists | Building identifiers from `request.args["sort"]` |
| `ORDER BY` fragments from developer-defined maps | Concatenating user input into SQL text |
| User **values** via bind parameters (`col_eq`, …) | f-strings with user input as column names |

```python
from sqlphilosophy.trusted_sql import (
    col_eq,
    col_icontains,
    col_range,
    literal_order_expr,
    order_by_allowlist,
    order_expr_from_sort,
    sql_table,
)

# SAFE — developer-defined table/column names
tbl = sql_table("user", "id", "email")
crit, params = col_eq("user.email", "email", user_supplied_email)  # value bound

# UNSAFE — never do this
# col_name = request.args["column"]
# col_eq(col_name, "v", value)  # user controls identifier
```

---

## Helper usage in repository workflows

```python
from sqlalchemy import select

ALLOWED_ORDER = frozenset({"email_asc", "email_desc"})
ORDER_MAP = {"email_asc": "user.email ASC", "email_desc": "user.email DESC"}

crit, params = col_eq("user.is_active", "active", True)
search = col_icontains("user.email", "q", search_text)  # None when empty
rng, rng_params = col_range("user.id", "min_id", ">=", 100)

criteria = [crit]
binds = dict(params)
if search:
    criteria.append(search[0])
    binds.update(search[1])
criteria.append(rng)
binds.update(rng_params)

rows = user_repo.fetch_statement_mappings(
    select(User.id, User.email).where(*criteria),
    params=binds,
)

order_col = order_by_allowlist("email_asc", ORDER_MAP, allowlist=ALLOWED_ORDER)
order_col = literal_order_expr("user.email DESC")
order_col = order_expr_from_sort("email", "asc", columns={"email": {"asc": "user.email ASC", "desc": "user.email DESC"}})
```

Async repositories use the same trusted helpers; pass bind params to `await repo.fetch_statement_mappings(...)`.

See [SECURITY.md](../../SECURITY.md) and [sorting-pagination.md](./sorting-pagination.md) for literal sort config.

**Next:** [sql-helpers.md](./sql-helpers.md) · [mapping-helpers.md](./mapping-helpers.md)
