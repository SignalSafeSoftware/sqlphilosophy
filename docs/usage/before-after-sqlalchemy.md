# Before and after: SQLAlchemy → sqlphilosophy

[← Repository guide](../repository-guide.md) · [Feature matrix](../feature-matrix.md)

Side-by-side examples showing how application code changes when you adopt sqlphilosophy repositories.

## What “before” and “after” mean

| | **Before** | **After** |
|---|-----------|----------|
| Where SQL lives | Routes, services, handlers call SQLAlchemy directly | Repositories and typed domain methods encapsulate queries |
| Sessions | Your app still owns `Session` / `AsyncSession` | Same — repositories wrap the session |
| SQLAlchemy | Full Core/ORM expressions remain available | sqlphilosophy **organizes** common patterns; it does not replace SQLAlchemy |
| Transactions | Service commits / rollbacks | **Still the service** — normal repo methods flush/execute only |
| Security | App authorizes, validates input | **Still the app** — sqlphilosophy does not sandbox queries |

sqlphilosophy still uses SQLAlchemy expressions under the hood. Your app still owns **authorization**, **tenant isolation**, **migrations**, **connection pooling**, and **session configuration**.

Import APIs from explicit submodules (`sqlphilosophy.sync.repository`, …). The root package exports only `__version__`.

---

## Mini domain (used throughout)

```python
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True)
    company_id: Mapped[int] = mapped_column(BigInteger)
    created_on: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_on: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_on: Mapped[datetime | None] = mapped_column(default=None)
    memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    company_id: Mapped[int] = mapped_column(BigInteger)
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    user: Mapped[User] = relationship(back_populates="memberships")
    project: Mapped[Project] = relationship(back_populates="members")


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    total_cents: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")
```

---

## Repository setup

### Before — SQLAlchemy in the service

```python
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_active_users(session: Session, company_id: int) -> list[User]:
    stmt = select(User).where(User.company_id == company_id, User.is_active.is_(True))
    return list(session.scalars(stmt).all())
```

### After — generic repository

```python
from sqlphilosophy.sync.repository import BaseRepository


def list_active_users(session: Session, company_id: int) -> list[User]:
    repo = BaseRepository(User, session)
    return list(repo.filter(company_id=company_id, is_active=True))
```

### After — typed repository + factory

```python
class UserRepository(BaseRepository[User, "AppFactory"]):
    def __init__(self, session: Session, factory: AppFactory) -> None:
        super().__init__(User, session, factory)

    def list_active_for_company(self, company_id: int) -> list[User]:
        return list(self.filter(company_id=company_id, is_active=True))


def list_active_users(factory: AppFactory, company_id: int) -> list[User]:
    return factory.users().list_active_for_company(company_id)
```

Async: use `AsyncSession`, `AsyncBaseRepository`, and `await` on repository terminals.

---

## SELECT workflows

### A. Filtered paginated list with dynamic sorting

#### Before (sync)

```python
from sqlalchemy import func, select

SORT = {"email": User.email, "name": User.name}


def active_user_page(session: Session, *, page: int, size: int, search: str | None, sort_key: str, sort_dir: str):
    base = select(User).where(User.is_active.is_(True), User.deleted_on.is_(None))
    if search:
        base = base.where(User.email.ilike(f"%{search}%"))
    order_col = SORT.get(sort_key, User.email)
    order = order_col.desc() if sort_dir == "desc" else order_col.asc()
    rows = session.scalars(base.order_by(order).limit(size).offset((page - 1) * size)).all()
    total = session.scalar(select(func.count()).select_from(base.subquery()))
    return rows, int(total or 0)
```

#### After (sync)

```python
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec


USER_SORT = SortConfig(
    default=SortSpec("email", "asc"),
    columns={
        "email": {"asc": User.email, "desc": User.email.desc()},
        "name": {"asc": User.name, "desc": User.name.desc()},
    },
    invalid="raise",
)


def active_user_page(repo: BaseRepository[User, object], *, page: int, size: int, search: str | None, order_by: dict[str, str]):
    builder = repo.statement().where(User.is_active.is_(True), User.deleted_on.is_(None))
    if search:
        builder = builder.where(User.email.ilike(f"%{search}%"))
    list_query = ListQuery.from_page(page=page, size=size, order_by=order_by)
    rows, total = builder.fetch_page(list_query, sort=USER_SORT)
    return rows, total  # tuple — not page.total
```

#### After (async)

```python
async def active_user_page(repo, *, page: int, size: int, search: str | None, order_by: dict[str, str]):
    builder = repo.statement().where(User.is_active.is_(True), User.deleted_on.is_(None))
    if search:
        builder = builder.where(User.email.ilike(f"%{search}%"))
    list_query = ListQuery.from_page(page=page, size=size, order_by=order_by)
    rows, total = await builder.fetch_page(list_query, sort=USER_SORT)
    return rows, total
```

---

### B. Joined aggregate query

#### Before (sync)

```python
def project_counts(session: Session, company_id: int) -> list[dict]:
    stmt = (
        select(User.id, User.email, func.count(ProjectMember.id).label("project_count"))
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(User.company_id == company_id, User.is_active.is_(True))
        .group_by(User.id, User.email)
        .having(func.count(ProjectMember.id) > 0)
    )
    return [dict(row) for row in session.execute(stmt).mappings().all()]
```

#### After (sync) — builder

```python
def project_counts(repo: BaseRepository[User, object], company_id: int) -> list[dict]:
    rows = (
        repo.statement()
        .select_columns(User.id, User.email, func.count(ProjectMember.id).label("project_count"))
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(User.company_id == company_id, User.is_active.is_(True))
        .group_by(User.id, User.email)
        .having(func.count(ProjectMember.id) > 0)
        .mappings()
        .all()
    )
    return rows
```

#### After (sync) — typed method

```python
class UserRepository(BaseRepository[User, AppFactory]):
    def project_counts(self, company_id: int) -> list[RowMapping]:
        return (
            self.statement()
            .select_columns(User.id, User.email, func.count(ProjectMember.id).label("project_count"))
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(User.company_id == company_id, User.is_active.is_(True))
            .group_by(User.id, User.email)
            .mappings()
            .all()
        )
```

Async: `await repo.statement().…mappings().all()`.

---

### C. Complex CTE / subquery

#### Before (sync)

```python
def users_with_open_invoices(session: Session) -> list[User]:
    open_inv = (
        select(Invoice.user_id)
        .where(Invoice.status == "open")
        .group_by(Invoice.user_id)
        .subquery()
    )
    stmt = select(User).join(open_inv, User.id == open_inv.c.user_id).where(User.is_active.is_(True))
    return list(session.scalars(stmt).all())
```

#### After (sync)

```python
def users_with_open_invoices(repo: BaseRepository[User, object]) -> list[User]:
    open_users = (
        repo.statement()
        .select_columns(Invoice.user_id)
        .select_from(Invoice)
        .where(Invoice.status == "open")
        .group_by(Invoice.user_id)
    )
    cte = open_users.as_cte("open_invoice_users")
    return (
        repo.statement()
        .where(User.is_active.is_(True))
        .join(cte, User.id == cte.c.user_id)
        .scalars()
        .all()
    )
```

Sync-only helper: `from sqlphilosophy.sync.query import cte_from` for standalone SELECT objects.

---

### D. Row locking / work queue

#### Before (sync)

```python
def claim_next_invoice(session: Session) -> Invoice | None:
    stmt = (
        select(Invoice)
        .where(Invoice.status == "queued")
        .order_by(Invoice.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    return session.scalar(stmt)
```

#### After (sync)

```python
def claim_next_invoice(repo: BaseRepository[Invoice, object]) -> Invoice | None:
    return (
        repo.statement()
        .where(Invoice.status == "queued")
        .order_by(Invoice.id)
        .with_for_update(skip_locked=True)
        .limit(1)
        .scalars()
        .first()
    )
```

`with_for_update` behavior is **dialect-dependent**. Async: `await repo.statement().…scalars().first()`.

---

## INSERT workflows

### A. Simple create

#### Before

```python
def create_user(session: Session, email: str, name: str) -> User:
    user = User(email=email, name=name, company_id=1)
    session.add(user)
    session.flush()
    session.commit()
    return user
```

#### After

```python
def create_user(session: Session, email: str, name: str) -> User:
    repo = BaseRepository(User, session)
    user = repo.create(email=email, name=name, company_id=1)  # flush only
    session.commit()  # caller commits
    return user
```

### B. Add existing object

| Before | After |
|--------|-------|
| `session.add(obj); session.flush()` | `repo.add(obj)` |

### C. Get-or-create

#### Before

```python
def get_or_create_user(session: Session, email: str) -> tuple[User, bool]:
    existing = session.scalar(select(User).where(User.email == email))
    if existing:
        return existing, False
    user = User(email=email, name=email.split("@")[0])
    session.add(user)
    session.flush()
    return user, True
```

#### After

```python
def get_or_create_user(session: Session, email: str) -> tuple[User, bool]:
    repo = BaseRepository(User, session)
    return repo.get_or_create(defaults={"name": email.split("@")[0]}, email=email)
```

### D. Typed repository insert

```python
class UserRepository(BaseRepository[User, AppFactory]):
    def register_user(self, email: str, name: str, company_id: int) -> User:
        return self.create(email=email, name=name, company_id=company_id)


def register(session: Session, factory: AppFactory, email: str, name: str) -> User:
    user = factory.users().register_user(email, name, company_id=1)
    session.commit()
    return user
```

Async: `await repo.create(...)`, `await session.commit()`.

---

## UPDATE workflows

### A. Partial update with writable allowlist

#### Before

```python
WRITABLE = {"name", "is_active"}


def patch_user(session: Session, user_id: int, payload: dict) -> int:
    values = {k: v for k, v in payload.items() if k in WRITABLE}
    if not values:
        return 0
    result = session.execute(update(User).where(User.id == user_id).values(**values))
    session.commit()
    return result.rowcount or 0
```

#### After

```python
def patch_user(session: Session, user_id: int, payload: dict) -> int:
    repo = BaseRepository(User, session)
    count = repo.update_partial(user_id, payload, frozenset({"name", "is_active"}))
    session.commit()
    return count
```

### B. Bulk criteria update

| Before | After |
|--------|-------|
| `session.execute(update(User).where(...).values(...))` | `repo.update_where(criteria=[...], values={...})` then `session.commit()` |

### C. Audit / timestamp-aware update

#### Before

```python
def patch_with_audit(session: Session, user_id: int, payload: dict, actor_id: int) -> int:
    values = {k: v for k, v in payload.items() if k in WRITABLE}
    values["updated_on"] = datetime.utcnow()
    # manual actor columns if your schema has them
    ...
```

#### After

```python
from sqlphilosophy.audit.context import audit_context
from sqlphilosophy.audit.listener import configure_audit_listeners

configure_audit_listeners()  # once at startup


def patch_with_audit(session: Session, repo: BaseRepository[User, object], user_id: int, payload: dict, actor_id: int) -> int:
    with audit_context(actor_id=actor_id):
        count = repo.update_partial(user_id, payload, frozenset({"name", "is_active"}), touch_updated_on=True)
    session.commit()
    return count
```

Audit mixin models use the **ORM setattr path** and **flush** (no commit).

### D. Empty update payload

Both `update_partial` and `update_where(..., values={})` return **`0`** without executing DML.

Async: `await repo.update_partial(...)`, `await repo.update_where(...)`.

---

## DELETE workflows

> Authorize destructive operations in application code before calling repository helpers.

### A. Delete by primary key

| Before | After |
|--------|-------|
| `session.execute(delete(User).where(User.id == id)); bool(rowcount)` | `repo.remove(id)` → `bool`; then `session.commit()` |

### B. Delete many IDs

| Before | After |
|--------|-------|
| `delete(User).where(User.id.in_(ids))` | `repo.delete_many(ids)` |

### C. Delete by criteria

#### Before

```python
def deactivate_deleted_users(session: Session) -> int:
    ids = session.scalars(select(User.id).where(User.deleted_on.is_not(None))).all()
    if not ids:
        return 0
    result = session.execute(delete(User).where(User.id.in_(ids)))
    session.commit()
    return result.rowcount or 0
```

#### After

```python
def purge_soft_deleted(session: Session) -> int:
    repo = BaseRepository(User, session)
    count = repo.delete_where(criteria=[User.deleted_on.is_not(None)])
    session.commit()
    return count
```

With bind params: `repo.delete_where(criteria=[User.company_id == bindparam("cid")], params={"cid": company_id})`.

### D. Delete all rows

> **Dangerous** — dev/ops only.

| Before | After |
|--------|-------|
| `session.execute(delete(User))` | `repo.delete_all()` — no commit until service commits |

### E. Batched purge

#### Before

```python
def purge_inactive(session: Session, batch_size: int = 500) -> int:
    total = 0
    while True:
        ids = session.scalars(
            select(User.id).where(User.is_active.is_(False)).limit(batch_size)
        ).all()
        if not ids:
            break
        session.execute(delete(User).where(User.id.in_(ids)))
        session.commit()
        total += len(ids)
    return total
```

#### After

```python
def purge_inactive(session: Session, *, authorized: bool) -> int:
    if not authorized:
        raise PermissionError("not authorized")
    repo = BaseRepository(User, session)
    return repo.batched_purge_ids(criteria=[User.is_active.is_(False)], batch_size=500)
    # commits each batch inside batched_purge_ids; batch_size must be >= 1
```

Async: `await repo.remove(...)`, `await repo.batched_purge_ids(...)`.

---

## Mapping helpers

### A. Raw select → dictionaries

| Before | After |
|--------|-------|
| `[dict(r) for r in session.execute(stmt, params).mappings().all()]` | `repo.fetch_statement_mappings(stmt, params)` |

### B. First / one row

| Before | After |
|--------|-------|
| `session.execute(...).mappings().first()` | `repo.fetch_mapping_first(stmt, params)` |
| `session.execute(...).mappings().one()` | `repo.fetch_mapping_one(stmt, params)` |

### C. Scalar count

| Before | After |
|--------|-------|
| `int(session.execute(count_stmt).scalar_one())` | `repo.scalar_count(count_stmt, params)` |

### D. Mapping pagination

| Before | After |
|--------|-------|
| `stmt.limit(n).offset(o)` + execute | `repo.fetch_mappings_page(stmt, limit=n, offset=o, params=...)` |

### E. Sorted mapping page

#### Before

```python
stmt = select(User.id, User.email).where(User.is_active.is_(True))
stmt = stmt.order_by(User.email.asc()).limit(20).offset(0)
rows = session.execute(stmt).mappings().all()
```

#### After

```python
sort = SortConfig(default=SortSpec("email", "asc"), columns={"email": {"asc": User.email, "desc": User.email.desc()}})
list_query = ListQuery.from_page(page=1, size=20, order_by={"email": "asc"})
rows = repo.fetch_sorted_mappings(select(User.id, User.email), list_query=list_query, sort=sort)
```

Async: prefix repository mapping calls with `await`.

---

## Trusted SQL

### Unsafe before

```python
from sqlalchemy import text

# NEVER — user controls identifier and value
stmt = text(f"select * from user where {request.args['field']} = '{request.args['value']}'")
rows = session.execute(stmt).mappings().all()
```

### Safe after — allowlisted filters + bind params

```python
from sqlalchemy import select

from sqlphilosophy.trusted_sql import col_eq, col_icontains, col_range, order_by_allowlist

ALLOWED_FIELDS = frozenset({"email", "is_active"})
ORDER_KEYS = frozenset({"email_asc", "email_desc"})
ORDER_MAP = {"email_asc": "user.email ASC", "email_desc": "user.email DESC"}

crit, params = col_eq("user.email", "email", user_email)  # value bound
search = col_icontains("user.name", "q", search_text)     # None if empty
rng, rng_params = col_range("user.id", "min_id", ">=", min_id)

criteria = [crit]
binds = dict(params)
if search:
    criteria.append(search[0])
    binds.update(search[1])
binds.update(rng_params)

rows = repo.fetch_statement_mappings(select(User.id, User.email).where(*criteria), params=binds)
order = order_by_allowlist(client_order_key, ORDER_MAP, allowlist=ORDER_KEYS)
```

Rules:

- User input may choose an **allowlisted key**, never a raw SQL identifier.
- User **values** are bind parameters.
- Table/column/`ORDER BY` fragments are **developer-defined**.

See [trusted-sql.md](./trusted-sql.md).

---

## Typed repository consolidation

### Before — SQL scattered in service

```python
def user_dashboard(session: Session, email: str) -> dict:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise LookupError(email)
    count = session.scalar(
        select(func.count()).select_from(ProjectMember).where(ProjectMember.user_id == user.id)
    )
    session.execute(update(User).where(User.id == user.id, User.is_active.is_(False)).values(is_active=False))
    session.commit()
    return {"user": user, "projects": int(count or 0)}
```

### After — typed repositories + single commit

```python
class UserRepository(BaseRepository[User, AppFactory]):
    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def active_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
        return self.statement().where(User.is_active.is_(True)).fetch_page(query, sort=USER_SORT)

    def project_counts(self, company_id: int) -> list[RowMapping]:
        return (
            self.statement()
            .select_columns(User.id, func.count(ProjectMember.id).label("n"))
            .join(ProjectMember)
            .where(User.company_id == company_id)
            .group_by(User.id)
            .mappings()
            .all()
        )

    def deactivate(self, user_id: int) -> int:
        return self.update_partial(user_id, {"is_active": False}, frozenset({"is_active"}))


class ProjectRepository(BaseRepository[Project, AppFactory]):
    def for_user(self, user_id: int) -> list[Project]:
        return list(
            self.statement()
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .scalars()
            .all()
        )


def user_dashboard(factory: AppFactory, session: Session, email: str) -> dict:
    users = factory.users()
    user = users.get_by_email(email)
    if user is None:
        raise LookupError(email)
    projects = factory.projects().for_user(user.id)
    users.deactivate(user.id)
    session.commit()
    return {"user": user, "projects": projects}
```

Async: `await` on typed methods and `await session.commit()`.

See [strongly-typed-repositories.md](./strongly-typed-repositories.md).

---

## When not to use a repository helper

- **Highly specialized SQL** (window functions, dialect-specific features) — keep using SQLAlchemy directly or a thin wrapper method on your typed repo.
- **Advanced reads** — `repo.statement()` still composes SQLAlchemy expressions; you are not limited to CRUD helpers.
- **One-off admin scripts** — direct Core/ORM may be clearer.
- **Not every query needs a named method** — use generic `BaseRepository` + builder until a pattern repeats.

sqlphilosophy is an **organization layer**, not an ORM replacement.

---

## Migration checklist

- [ ] Identify repeated CRUD and list/count patterns per model.
- [ ] Wrap each model with `BaseRepository` / `AsyncBaseRepository`.
- [ ] Move route/service SQL into typed repository methods as patterns stabilize.
- [ ] Replace manual pagination + count with `ListQuery` + `fetch_page` (returns `(rows, total)`).
- [ ] Replace manual PATCH filtering with `update_partial` + `writable` allowlists.
- [ ] Replace ad-hoc delete loops with `delete_where` or authorized `batched_purge_ids`.
- [ ] Keep **commits in the service / unit-of-work** layer (except batched purge batches).
- [ ] Move string-interpolated SQL to `sqlphilosophy.trusted_sql` + bind params.
- [ ] Add tests for typed repository methods (SQLite in-memory is fine).
- [ ] Register audit listeners once if using audit mixins.

---

## Common before/after summary

| Concern | Direct SQLAlchemy before | sqlphilosophy after |
|---------|--------------------------|---------------------|
| Create + flush | `add` + `flush` | `repo.create` / `repo.add` (flush; **no commit**) |
| Required get | `scalar(select…)` + manual error | `repo.get(id)` → `LookupError` |
| Optional get | `scalar(select…)` | `repo.get_by_id(id)` |
| Paginated list | `limit`/`offset` + separate count | `repo.statement().fetch_page(ListQuery…)` → `(rows, total)` |
| Sort allowlist | manual dict + `order_by` | `SortConfig` + `apply_sort` / `fetch_page`; `invalid="raise"` |
| Partial update | `update().values()` + manual filter | `repo.update_partial(id, fields, writable)` |
| Bulk update | `update().where().values()` | `repo.update_where(criteria, values)` |
| Delete one | `delete().where(pk)` | `repo.remove(id)` |
| Delete many | `delete().where(id.in_(…))` | `repo.delete_many(ids)` |
| Criteria delete | select IDs + delete | `repo.delete_where(criteria, params)` |
| Batched purge | loop select/delete/commit | `repo.batched_purge_ids` (**commits each batch**) |
| Mapping rows | `execute().mappings()` | `repo.fetch_statement_mappings` / `iter_mappings` |
| Raw trusted filters | string SQL (unsafe) | `trusted_sql.col_*` + `fetch_statement_mappings` |
| Typed cross-repo | imports + repeated joins | `repo.for_repo(OtherRepository)` + domain methods |

---

## See also

- [setup.md](./setup.md) · [reads.md](./reads.md) · [writes.md](./writes.md) · [deletes.md](./deletes.md)
- [query-builder.md](./query-builder.md) · [sorting-pagination.md](./sorting-pagination.md)
- [mapping-helpers.md](./mapping-helpers.md) · [trusted-sql.md](./trusted-sql.md)
- [strongly-typed-repositories.md](./strongly-typed-repositories.md)
