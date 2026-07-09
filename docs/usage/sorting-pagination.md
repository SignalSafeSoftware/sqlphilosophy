# Pagination and sorting

[← Repository guide](../repository-guide.md) · [Setup](./setup.md)

Shared module: `sqlphilosophy.sorting`.

---

## `ListQuery.from_page`

```python
from sqlphilosophy.sorting import ListQuery

list_query = ListQuery.from_page(page=1, size=20, order_by={"email": "asc"})
# list_query.offset, list_query.limit, list_query.order_by
```

## `SortSpec` and ORM-column `SortConfig`

```python
from sqlphilosophy.sorting import SortConfig, SortSpec

sort = SortConfig(
    default=SortSpec("email", "asc"),
    columns={
        "email": {"asc": User.email, "desc": User.email.desc()},
        "name": {"asc": User.display_name, "desc": User.display_name.desc()},
    },
)
```

## Literal SQL / trusted sort config

```python
sort = SortConfig(
    default=SortSpec("email", "asc"),
    literal_sql=True,
    columns={"email": {"asc": "user.email ASC", "desc": "user.email DESC"}},
)
```

Literal fragments must be **developer-defined**. See [trusted-sql.md](./trusted-sql.md).

## Custom resolver

```python
def resolve(spec: SortSpec) -> object:
    if spec.column == "email":
        return User.email.desc() if spec.direction == "desc" else User.email.asc()
    raise ValueError(f"unsupported: {spec.column}")

sort = SortConfig(default=SortSpec("email", "asc"), resolver=resolve)
```

## `invalid="default"` vs `invalid="raise"`

```python
# default — bad client order_by falls back to default SortSpec
permissive = SortConfig(default=SortSpec("email", "asc"), columns={...}, invalid="default")

# strict — raises ValueError for bad column or direction
strict = SortConfig(default=SortSpec("email", "asc"), columns={...}, invalid="raise")
strict.resolve_spec({"not_a_column": "asc"})  # ValueError
```

## With repository mapping helpers and builder `fetch_page`

```python
# mapping helper
rows = user_repo.fetch_sorted_mappings(select(User.id, User.email), list_query=list_query, sort=sort)

# builder terminal
rows, total = user_repo.statement().fetch_page(list_query, sort=sort)

# async
rows, total = await user_repo.statement().fetch_page(list_query, sort=sort)
```

Repository `filter(..., page=, limit=)` uses **1-based pages** directly; builder `fetch_page` uses `ListQuery` offset/limit.

**Next:** [query-builder.md](./query-builder.md) · [mapping-helpers.md](./mapping-helpers.md)
