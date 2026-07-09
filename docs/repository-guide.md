# sqlphilosophy repository guide

Entry point for application-level usage of `BaseRepository` and `AsyncBaseRepository`. Detailed code examples live in [usage/](./usage/); the [feature matrix](./feature-matrix.md) is the compact sync/async API reference.

Runnable typed-repository demos:

- [docs/examples/typed_repository_sync.py](./examples/typed_repository_sync.py)
- [docs/examples/typed_repository_async.py](./examples/typed_repository_async.py)

---

## Overview

### What a repository wraps

One repository wraps **one SQLAlchemy mapped model** and one **session** (`Session` or `AsyncSession`). It is the application-facing entry point for CRUD, fluent reads, mapping helpers, and (optionally) cross-model navigation through a factory.

### What this package does

- Sync and async repository CRUD (`BaseRepository`, `AsyncBaseRepository`)
- Fluent statement builders with pagination, sort, joins, and terminals
- Core SQL helpers and trusted SQL fragments
- Optional audit listeners and timestamp mixins

### What this package does **not** do

This package does **not** handle **authorization**, **migrations**, **tenant isolation**, **query sandboxing**, or **connection pooling**. Your application owns engine/session lifecycle, access control, and schema management.

### Transaction ownership

| Operation | Commit behavior |
|-----------|-----------------|
| `create`, `add`, `get_or_create` (when creating) | **Flush only** — caller commits |
| `update_partial`, `update_where`, `remove`, `delete_many`, `delete_where`, `delete_all` | Execute DML; **no commit** |
| `batched_purge_ids(..., batch_size=...)` | **Commits after each batch**; requires `batch_size >= 1` |

### Sync vs async mental model

| Sync | Async |
|------|-------|
| `Session` | `AsyncSession` |
| `BaseRepository` | `AsyncBaseRepository` |
| Direct calls: `repo.get(id)` | `await repo.get(id)` |
| Builder terminals: `builder.scalar()` | `await builder.scalar()` |
| `sqlphilosophy.sql` session helpers | Use sync `Session` or repository async methods |

Import APIs from explicit submodules (`sqlphilosophy.sync.repository`, `sqlphilosophy.aio.repository`, …). The root package exports only `__version__`.

---

## Strongly typed repositories

Subclass `BaseRepository[Model, AppFactory]` / `AsyncBaseRepository[Model, AppFactory]` in **your application**, add domain methods (`get_by_email`, `search_page`, …), and wire a **session-scoped factory** that implements `RepositoryFactory` / `AsyncRepositoryFactory` with cached typed repos.

- **Full guide:** [usage/strongly-typed-repositories.md](./usage/strongly-typed-repositories.md) — protocols, type aliases, services, cross-repo workflows, recommended layout, common mistakes.
- **Runnable demos:** [typed_repository_sync.py](./examples/typed_repository_sync.py), [typed_repository_async.py](./examples/typed_repository_async.py)

Use `factory.get_repository(UserRepository)` for typed access, `factory.repository(User)` for generic CRUD, and `repo.for_repo(OrderRepository)` to hop between repos on the same session. Pass a factory whenever you call `for_repo()`.

**Migrating from raw SQLAlchemy?** See [usage/before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md) for side-by-side SELECT/INSERT/UPDATE/DELETE examples.

---

## Usage guide — table of contents

| Topic | Page |
|-------|------|
| Setup, shared models, sync/async lifecycle | [usage/setup.md](./usage/setup.md) |
| Basic reads (`get`, `filter`, joins, eager load) | [usage/reads.md](./usage/reads.md) |
| Creates, updates, commit/rollback | [usage/writes.md](./usage/writes.md) |
| Deletes and destructive helpers | [usage/deletes.md](./usage/deletes.md) |
| Mapping helpers through the repository | [usage/mapping-helpers.md](./usage/mapping-helpers.md) |
| Fluent query builder (composition + terminals) | [usage/query-builder.md](./usage/query-builder.md) |
| Pagination and sorting (`ListQuery`, `SortConfig`) | [usage/sorting-pagination.md](./usage/sorting-pagination.md) |
| Typed repositories and factories | [usage/typed-repositories.md](./usage/typed-repositories.md) |
| **Strongly typed repositories** | [usage/strongly-typed-repositories.md](./usage/strongly-typed-repositories.md) |
| **Before/after SQLAlchemy** | [usage/before-after-sqlalchemy.md](./usage/before-after-sqlalchemy.md) |
| SQL helpers (`sqlphilosophy.sql`) | [usage/sql-helpers.md](./usage/sql-helpers.md) |
| Trusted SQL boundaries | [usage/trusted-sql.md](./usage/trusted-sql.md) |
| Audit listeners and mixins | [usage/audit.md](./usage/audit.md) |
| Version and typing aliases | [usage/types-version.md](./usage/types-version.md) |

---

## Quick reference

- **API map:** [feature-matrix.md](./feature-matrix.md)
- **All usage pages:** [usage/](./usage/)
- **Typed factory demos:** [typed_repository_sync.py](./examples/typed_repository_sync.py), [typed_repository_async.py](./examples/typed_repository_async.py)
- **Security / trust boundaries:** [SECURITY.md](../SECURITY.md)
