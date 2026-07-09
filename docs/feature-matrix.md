# sqlphilosophy feature matrix

Quick map of package capabilities and their sync/async availability. For workflow-oriented examples, see [repository-guide.md](./repository-guide.md) and the [usage guide](./usage/). Runnable typed-repository demos live in [docs/examples/](./examples/).

**Legend**

| Symbol | Meaning |
|--------|---------|
| ✅ | Available (sync or async column) |
| — | Not applicable |
| **Shared** | Same module/API for both stacks |
| **Sync-only** | Uses `Session` or lives under `sqlphilosophy.sync` |
| **Async-only** | Uses `AsyncSession` or lives under `sqlphilosophy.aio` |

**Transaction defaults**

| Pattern | Commit behavior | Examples |
|---------|-----------------|----------|
| Normal CRUD (`create`, `add`, `update_partial`, `remove`, `delete_*`, `update_where`, …) | Stages/flushes or executes DML; **caller commits** | [writes](./usage/writes.md), [deletes](./usage/deletes.md) |
| `batched_purge_ids` | **Commits after each batch** (destructive, app-authorized) | [deletes](./usage/deletes.md) |

**Examples index** — jump from API group to code:

| Feature area | Usage guide |
|--------------|-------------|
| Setup, models, sessions | [usage/setup.md](./usage/setup.md) |
| Basic reads | [usage/reads.md](./usage/reads.md) |
| Creates, updates | [usage/writes.md](./usage/writes.md) |
| Deletes (incl. bulk) | [usage/deletes.md](./usage/deletes.md) |
| Mapping helpers | [usage/mapping-helpers.md](./usage/mapping-helpers.md) |
| Query builder | [usage/query-builder.md](./usage/query-builder.md) |
| Pagination & sorting | [usage/sorting-pagination.md](./usage/sorting-pagination.md) |
| Typed repos & factories | [usage/typed-repositories.md](./usage/typed-repositories.md) · [strongly-typed-repositories.md](./usage/strongly-typed-repositories.md) |
| SQL helpers | [usage/sql-helpers.md](./usage/sql-helpers.md) |
| Trusted SQL | [usage/trusted-sql.md](./usage/trusted-sql.md) |
| Audit | [usage/audit.md](./usage/audit.md) |
| Version & types | [usage/types-version.md](./usage/types-version.md) |
| Before/after SQLAlchemy | [usage/before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md) |
| Overview & transactions | [repository-guide.md](./repository-guide.md#transaction-ownership) |

This package does **not** provide authorization, migrations, tenant isolation, query sandboxing, or connection pooling.

---

## Repository lifecycle

→ [setup.md](./usage/setup.md) · [typed-repositories.md](./usage/typed-repositories.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#repository-setup)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Construct repo for one model | `BaseRepository(model, session, factory=None)` | `AsyncBaseRepository(model, session, factory=None)` | Requires single-column PK |
| ORM mapper inspection | `inspect_model` / `inspect()` | same | Class + instance helpers |
| Connection metadata | `list_table_names()`, `has_table(name)` | `await list_table_names()`, `await has_table(name)` | Dev/diagnostic |
| Default read builder | `statement()` → `StatementQueryBuilder` | `statement()` → `AsyncStatementQueryBuilder` | Uses factory when provided |
| Cross-repo access | `for_repo(RepoClass)` | `for_repo(RepoClass)` | Requires factory; raises if missing |

---

## Basic reads

→ [reads.md](./usage/reads.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#select-workflows)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| PK lookup (nullable) | `get_by_id(id, load_relations=None)` | `await get_by_id(...)` | Optional `LoaderOption` sequence |
| PK lookup (required) | `get(id, load_relations=None)` | `await get(...)` | Raises `LookupError` if missing |
| Multiple PKs | `get_many(ids, load_relations=None)` | `await get_many(...)` | Empty `ids` → `[]` |
| PK exists | `exists(id)` | `await exists(id)` | |
| Filtered exists | `exists_where(**filters)` | `await exists_where(**filters)` | Equality `filter_by` semantics |
| Row count | `count(**filters)` | `await count(**filters)` | Optional equality filters |
| First match | `first(load_relations=None, **filters)` | `await first(...)` | |
| Filtered list | `filter(page=1, limit=None, load_relations=None, **filters)` | `await filter(...)` | Paginated optional |
| All rows | `get_all(page=1, limit=None, load_relations=None)` | `await get_all(...)` | Ordered by PK |
| Explicit join tuples | `get_with_join(target_model, *filters, join_on=None)` | `await get_with_join(...)` | Returns `(base, target)` pairs |
| Eager loading | `load_relations=[selectinload(...), ...]` on read methods | same | Pass SQLAlchemy `LoaderOption`s |

---

## Basic writes

→ [writes.md](./usage/writes.md) (`remove` → [deletes.md](./usage/deletes.md)) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#insert-workflows)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Create + flush | `create(**fields)` | `await create(**fields)` | Builds model, calls `add` |
| Stage instance | `add(obj)` | `await add(obj)` | **Flush only; no commit** |
| Upsert-style | `get_or_create(defaults=None, **lookup)` | `await get_or_create(...)` | Returns `(obj, created)`; may flush on create |
| Partial update by PK | `update_partial(id, fields, writable, touch_updated_on=False)` | `await update_partial(...)` | Returns row count; audit models use ORM path + flush |
| Delete by PK | `remove(id)` → `bool` | `await remove(id)` | No commit |

---

## Bulk updates / deletes

→ [writes.md#updates](./usage/writes.md#updates) · [deletes.md](./usage/deletes.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#update-workflows)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Bulk UPDATE | `update_where(criteria, values, params=None)` | `await update_where(...)` | Empty `values` → `0`; no commit |
| Criteria delete | `delete_where(criteria, params=None)` | `await delete_where(...)` | PK lookup + `delete_many`; no commit |
| Delete many PKs | `delete_many(ids)` | `await delete_many(ids)` | No commit |

---

## Destructive helpers

> **Dangerous** — authorize in application code before calling.

→ [deletes.md](./usage/deletes.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#delete-workflows)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Delete all model rows | `delete_all()` | `await delete_all()` | Bulk DELETE; **no commit** |
| Batched criteria purge | `batched_purge_ids(criteria, batch_size)` | `await batched_purge_ids(...)` | **Commits each batch**; `batch_size >= 1` |

Prefer scoped `delete_where` in application code over `delete_all`.

---

## Mapping helpers

Raw SQL / Core statements executed through the repository session.

→ [mapping-helpers.md](./usage/mapping-helpers.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#mapping-helpers)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| All rows as dicts | `fetch_statement_mappings(stmt, params=None)` | `await fetch_statement_mappings(...)` | Normalized via `rows_mapping` |
| Stream dict rows | `iter_mappings(stmt, params=None)` | `async for` via `iter_mappings` | Yields plain `dict`s |
| First mapping | `fetch_mapping_first(stmt, params=None)` | `await fetch_mapping_first(...)` | |
| Exactly one mapping | `fetch_mapping_one(stmt, params=None)` | `await fetch_mapping_one(...)` | SQLAlchemy `one()` semantics |
| Page of mappings | `fetch_mappings_page(stmt, limit, offset, params=None)` | `await fetch_mappings_page(...)` | |
| Sorted page | `fetch_sorted_mappings(stmt, list_query, params=None, sort=None)` | `await fetch_sorted_mappings(...)` | Applies `SortConfig` when given |
| Scalar count query | `scalar_count(stmt, params=None)` | `await scalar_count(...)` | |

---

## Fluent query builder — composition

Builder entry: `repo.statement()` or `SqlAlchemyStatementBuilder(session, model)` / `AsyncSqlAlchemyStatementBuilder(session, model)`.

→ [query-builder.md#composition-methods](./usage/query-builder.md#composition-methods)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| SELECT entity | `.select_entity()` | same | ORM entity columns |
| SELECT table | `.select_table()` | same | Table-only projection |
| SELECT columns | `.select_columns(*cols)` | same | |
| FROM clause | `.select_from(clause)` | same | |
| INNER JOIN | `.join(target, onclause=None, isouter=False)` | same | |
| OUTER JOIN | `.outerjoin(target, onclause=None)` | same | |
| WHERE | `.where(*criteria)` | same | |
| Equality filters | `.filter_by(**kwargs)` | same | |
| DISTINCT | `.distinct()` / `.distinct(*columns)` | same | No args = portable; columns = PostgreSQL `DISTINCT ON` (not portable) |
| GROUP BY | `.group_by(*clauses)` | same | |
| Correlate | `.correlate(*froms)` / `.correlate_except(*froms)` | same | Subquery correlation |
| Lateral / CTE on builder | `.as_lateral(name)` / `.as_cte(name)` | same | Returns SQLAlchemy clause |
| ORDER BY | `.order_by(*clauses)` | same | |
| Client sort | `.apply_sort(sort, order_by=None)` | same | Uses `SortConfig` |
| LIMIT / OFFSET | `.limit(n)` / `.offset(n)` | same | `>= 0`; builder mutation |
| Bind params | `.with_params(params)` | same | Merged into execute |
| Row lock | `.with_for_update(of=None, skip_locked=False)` | same | Dialect-dependent |

**Sync-only module helpers** (not on async builder module):

→ [query-builder.md#composition-methods](./usage/query-builder.md#composition-methods) (see Lateral / CTE)

| Purpose | API | Notes |
|---------|-----|-------|
| Lateral from SELECT | `sqlphilosophy.sync.query.lateral_from(stmt, name)` | Standalone helper |
| CTE from SELECT | `sqlphilosophy.sync.query.cte_from(stmt, name)` | Standalone helper |

Async code can still use `.as_lateral()` / `.as_cte()` on the builder instance.

---

## Fluent query builder — terminal methods

→ [query-builder.md#terminal-methods](./usage/query-builder.md#terminal-methods)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Row mappings | `.mappings().all()` / `.first()` / `.one()` | `await .mappings().all()` / … | Chainable result objects |
| ORM scalars | `.scalars().all()` / `.first()` | `await .scalars().all()` / … | Entity instances |
| Single scalar | `.scalar()` | `await .scalar()` | First column, first row; `None` if empty |
| Required scalar | `.scalar_one()` | `await .scalar_one()` | Raises if zero/multiple |
| Count composed SELECT | `.count()` | `await .count()` | Ignores limit/offset/order on inner query |
| Count distinct columns | `.count_distinct(*columns)` | `await .count_distinct(...)` | `COUNT(DISTINCT …)`; portable |
| Paginated mappings + total | `.fetch_page(list_query, sort=None)` | `await .fetch_page(...)` | Returns `(rows, total)`; does not mutate builder |
| Debug SELECT | `.build_select()` | same | Inspect SQL only; prefer terminal execute methods |

---

## Pagination and sorting

→ [sorting-pagination.md](./usage/sorting-pagination.md)

| Purpose | Sync / async | Module | Notes |
|---------|--------------|--------|-------|
| Offset/limit slice | **Shared** | `sqlphilosophy.sorting.ListQuery` | Optional `order_by` map |
| Page helper | **Shared** | `ListQuery.from_page(page, size, order_by=None)` | 1-based page |
| Sort column + direction | **Shared** | `SortSpec(column, direction)` | `direction`: `"asc"` \| `"desc"` |
| Allowlisted client sort | **Shared** | `SortConfig(...)` | ORM columns, literal SQL, or custom resolver |
| Invalid sort policy | **Shared** | `SortConfig(..., invalid="default"\|"raise")` | `"default"` silently falls back; `"raise"` → `ValueError` |
| Resolve client sort | **Shared** | `sort.resolve_spec(order_by)` | |
| ORDER BY clauses | **Shared** | `sort.order_clauses(order_by)` | Used by builders / repos |

Repository pagination: `filter(..., page=, limit=)` and `get_all(..., page=, limit=)` use 1-based pages. Builder `fetch_page` uses `ListQuery` offset/limit.

---

## Typed repository factories

→ [strongly-typed-repositories.md](./usage/strongly-typed-repositories.md) · [typed-repositories.md](./usage/typed-repositories.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#typed-repository-consolidation) · [examples/typed_repository_sync.py](./examples/typed_repository_sync.py) · [examples/typed_repository_async.py](./examples/typed_repository_async.py)

| Purpose | Sync API | Async API | Notes |
|---------|----------|-----------|-------|
| Factory protocol | [`RepositoryFactory`](./usage/strongly-typed-repositories.md#protocols-for-service-layer-typing) | [`AsyncRepositoryFactory`](./usage/strongly-typed-repositories.md#protocols-for-service-layer-typing) | `sqlphilosophy.sync.protocols` / `aio.protocols` |
| Repository protocol | [`BaseRepositoryProtocol`](./usage/strongly-typed-repositories.md#protocols-for-service-layer-typing) | [`AsyncBaseRepositoryProtocol`](./usage/strongly-typed-repositories.md#protocols-for-service-layer-typing) | Typing surface for subclasses / services |
| Create builder | `factory.create_statement(model)` | same | |
| Cached typed repo | [`factory.get_repository(RepoClass)`](./usage/strongly-typed-repositories.md#sync-factory-and-caching) | same | App implements caching |
| Generic repo | [`factory.repository(model)`](./usage/strongly-typed-repositories.md#sync-factory-and-caching) | same | Returns protocol-typed CRUD |
| Subclass pattern | [`class UserRepo(BaseRepository[User, Factory])`](./usage/strongly-typed-repositories.md#sync-typed-repository) | [`AsyncBaseRepository[User, Factory]`](./usage/strongly-typed-repositories.md#async-typed-repository) | Add domain methods |
| Cross-repo | [`repo.for_repo(OtherRepo)`](./usage/strongly-typed-repositories.md#cross-repository-workflows) | same | Same session + factory |

---

## SQL helpers

**Sync-only** — functions in `sqlphilosophy.sql` take a `Session` (or are pure). Use from sync services or wrap async calls with care; async repositories implement partial updates internally.

→ [sql-helpers.md](./usage/sql-helpers.md)

| Purpose | API | Notes |
|---------|-----|-------|
| Row → dict | `row_mapping`, `row_mapping_opt`, `rows_mapping` | Normalization |
| Typed column accessors | `row_int`, `row_str`, `row_bool`, `row_float`, `row_json`, `row_uuid`, … and `row_opt_*` | From mapping rows |
| API dict accessors | `api_int`, `api_float` | With defaults |
| Partial update (ORM) | `partial_update_model(session, model, pk, fields, writable, …)` | Flush; no commit |
| Partial update (Core table) | `partial_update(session, table_name, pk, fields, writable, …)` | |
| Writable merge | `apply_writable_update(target, fields, writable)` | In-memory |
| Delete by IDs | `delete_by_ids`, `delete_by_ids_model` | |
| Criteria merge | `merge_criteria`, `combine_and` | |
| Count helpers | `count_composed_select`, `count_from_subquery`, `count_from_table` | |
| Paginated Core select | `select_page_from_table`, `apply_mappings_page` | |
| Sort column lookup | `get_sort_column` | |
| IN bind param | `expanding_in_param(name, values)` | Expanding bind |

---

## Trusted SQL helpers

**Shared** — `sqlphilosophy.trusted_sql` (re-exported from `sqlphilosophy.sql` for compatibility).

> **Trust boundary:** identifier/SQL-fragment parameters (`table_name`, `col_sql`, `ORDER BY` text, allowlists) must be **developer-defined**. User **values** use bind parameters only. Never build identifiers from request input.

→ [trusted-sql.md](./usage/trusted-sql.md) · [before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md#trusted-sql)

| Purpose | API | Notes |
|---------|-----|-------|
| Core table | `sql_table(name, *column_names)` | Trusted identifiers only |
| Equality filter + bind | `col_eq(col_sql, param_name, value)` | |
| Case-insensitive LIKE | `col_icontains(col_sql, param_name, raw)` | Returns `None` if empty search |
| Range filter | `col_range(col_sql, param_name, op, value)` | `>=` or `<=` |
| ORDER BY fragment | `literal_order_expr(spec)` | e.g. `"created_at DESC"` |
| Allowlisted ORDER BY | `order_by_allowlist(key, map, allowlist=…)` | |
| Sort metadata ORDER BY | `order_expr_from_sort(column, direction, columns=…)` | |

---

## Audit helpers

**Shared** modules; listeners attach to sync/async SQLAlchemy sessions configured by the app.

→ [audit.md](./usage/audit.md)

| Purpose | API | Notes |
|---------|-----|-------|
| Register listeners | `configure_audit_listeners()` | Call once at startup |
| Request-scoped actor | `audit_context(actor_id)` | Context manager |
| Read actor | `get_audit_actor_id()`, `get_audit_context()` | |
| Mixins | `TimestampModel`, `CreatedTimestampModel`, `UpdatedTimestampModel`, `SoftDeleteTimestampModel`, … | See `sqlphilosophy.audit.model` |
| Soft delete helper | `soft_delete(target, actor=None)` | Sets soft-delete fields |
| Audit field introspection | `AuditColumns`, `is_audit_model(instance)` | |

Audit records changes; it does **not** enforce authorization.

`update_partial` on audit mixin models uses the ORM setattr path and **flushes** (no commit). See [writes.md#audit-model-behavior](./usage/writes.md#audit-model-behavior).

---

## Root package metadata

→ [types-version.md#package-version](./usage/types-version.md#package-version)

| Purpose | API | Notes |
|---------|-----|-------|
| Package version | `sqlphilosophy.__version__` | Only public root export; from installed metadata or bundled `VERSION` file |

Import submodules explicitly for APIs (`sqlphilosophy.sync.repository`, `sqlphilosophy.aio.repository`, etc.).

---

## Typing aliases

**Shared** — `sqlphilosophy.types`

→ [types-version.md](./usage/types-version.md#common-typing-aliases-sqlphilosophytypes)

| Alias | Purpose |
|-------|---------|
| `PrimaryKey`, `IdList` | PK types for repository methods |
| `RowMapping`, `RowValue`, `ApiObject` | Row / API dict typing |
| `SqlFilter`, `SqlFilters`, `SqlSelect`, `SqlClause`, … | SQLAlchemy expression aliases |
| `SqlBindParams` | Execute bind dicts |
| `OrmModel` | Mapped class type |
| `JSONValue`, `JSONObject`, … | JSON-safe typing |
| `cursor_rowcount(result)` | DML rowcount helper (used by sync and async repos) |

---

## Quick sync ↔ async cheat sheet

→ [setup.md#async-setup](./usage/setup.md#async-setup) · [repository-guide.md#sync-vs-async-mental-model](./repository-guide.md#sync-vs-async-mental-model)

| Sync | Async |
|------|-------|
| `from sqlphilosophy.sync.repository import BaseRepository` | `from sqlphilosophy.aio.repository import AsyncBaseRepository` |
| `from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder` | `from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder` |
| `from sqlphilosophy.sync.protocols import RepositoryFactory` | `from sqlphilosophy.aio.protocols import AsyncRepositoryFactory` |
| `Session` | `AsyncSession` |
| Direct method calls | Prefix with `await` on repo/builder terminals and async-only repo methods |
| `sqlphilosophy.sql` session helpers | Use sync `Session` or repository async methods for the same workflows |
