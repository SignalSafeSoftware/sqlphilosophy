# Strongly typed repositories

[← Repository guide](../repository-guide.md) · [Feature matrix](../feature-matrix.md#typed-repository-factories)

How to structure **application-owned** domain repositories on top of sqlphilosophy’s generic `BaseRepository` / `AsyncBaseRepository`, factories, protocols, and typing aliases.

**Runnable end-to-end demos:**

- [docs/examples/typed_repository_sync.py](../examples/typed_repository_sync.py)
- [docs/examples/typed_repository_async.py](../examples/typed_repository_async.py)

sqlphilosophy provides base repositories and protocols; **your app** owns models, typed subclasses, factory wiring, and service-layer authorization.

---

## Pattern overview

1. Define SQLAlchemy models in your app.
2. Subclass `BaseRepository[Model, AppFactory]` (or async equivalent).
3. Add **domain methods** (`get_by_email`, `search_page`, …) that call repository/builder APIs.
4. Implement a **session-scoped factory** that caches typed repos and implements `RepositoryFactory` / `AsyncRepositoryFactory`.
5. Inject the factory (or typed repos) into services; **commit in the service**, not in repository methods.

---

## Models (shared starting point)

```python
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "order"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    user: Mapped[User] = relationship(back_populates="orders")
```

---

## Sync typed repository

```python
from typing import cast

from sqlalchemy.orm import Session

from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.types import PrimaryKey, RowMapping, SqlFilter


class UserRepository(BaseRepository[User, "AppRepositoryFactory"]):
    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def active_users(self) -> list[User]:
        return list(self.filter(is_active=True))

    def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
        sort = SortConfig(
            default=SortSpec("email", "asc"),
            columns={
                "email": {"asc": User.email, "desc": User.email.desc()},
                "name": {"asc": User.display_name, "desc": User.display_name.desc()},
            },
        )
        return self.statement().where(User.is_active.is_(True)).fetch_page(query, sort=sort)

    def pending_order_count(self, user_id: PrimaryKey) -> int:
        orders = self.for_repo(OrderRepository)
        return orders.count_for_user(user_id, status="pending")


class OrderRepository(BaseRepository[Order, "AppRepositoryFactory"]):
    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(Order, session, factory)

    def count_for_user(self, user_id: PrimaryKey, *, status: str | None = None) -> int:
        filters: dict[str, object] = {"user_id": user_id}
        if status is not None:
            filters["status"] = status
        return self.count(**filters)

    def orders_for_user(self, user_id: PrimaryKey) -> list[Order]:
        return list(self.filter(user_id=user_id))

    def list_for_user(self, user_id: PrimaryKey, *, criteria: list[SqlFilter] | None = None) -> list[Order]:
        builder = self.statement().where(Order.user_id == user_id)
        if criteria:
            builder = builder.where(*criteria)
        return builder.scalars().all()
```

---

## Sync factory and caching

```python
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, cast

from sqlalchemy.orm import DeclarativeBase, Session

from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R", bound='BaseRepository[T, "AppRepositoryFactory"]')  # type: ignore[valid-type]


class AppRepositoryFactory(RepositoryFactory, Protocol):
    def users(self) -> UserRepository: ...
    def orders(self) -> OrderRepository: ...


class SessionRepositoryFactory:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repositories: dict[Any, Any] = {}

    def create_statement(self, model: type[T]) -> StatementQueryBuilder[T]:
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type[R]) -> R:
        cached = self._repositories.get(repo_class)
        if cached is None:
            ctor = cast(Callable[[Session, AppRepositoryFactory], R], repo_class)
            cached = ctor(self._session, cast(AppRepositoryFactory, self))
            self._repositories[repo_class] = cached
        return cast(R, cached)

    def repository(self, model: type[T]) -> BaseRepository[T, AppRepositoryFactory]:
        return BaseRepository(model, self._session, cast(AppRepositoryFactory, self))

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)

    def orders(self) -> OrderRepository:
        return self.get_repository(OrderRepository)
```

**Access patterns:**

```python
factory = SessionRepositoryFactory(session)

typed = factory.get_repository(UserRepository)   # cached typed repo
generic = factory.repository(User)               # generic CRUD surface
via_shortcut = factory.users()                   # app-specific API

cross = typed.for_repo(OrderRepository)          # same session + factory
```

---

## Async typed repository

Mirror sync with `AsyncBaseRepository`, `await` on terminals, and `AsyncRepositoryFactory`:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from sqlphilosophy.aio.repository import AsyncBaseRepository


class AsyncUserRepository(AsyncBaseRepository[User, "AsyncAppRepositoryFactory"]):
    def __init__(self, session: AsyncSession, factory: AsyncAppRepositoryFactory) -> None:
        super().__init__(User, session, factory)

    async def get_by_email(self, email: str) -> User | None:
        return await self.first(email=email)

    async def active_users(self) -> list[User]:
        return list(await self.filter(is_active=True))

    async def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
        sort = SortConfig(
            default=SortSpec("email", "asc"),
            columns={"email": {"asc": User.email, "desc": User.email.desc()}},
        )
        return await self.statement().where(User.is_active.is_(True)).fetch_page(query, sort=sort)

    async def pending_order_count(self, user_id: PrimaryKey) -> int:
        orders = self.for_repo(AsyncOrderRepository)
        return await orders.count_for_user(user_id, status="pending")


class AsyncOrderRepository(AsyncBaseRepository[Order, "AsyncAppRepositoryFactory"]):
    def __init__(self, session: AsyncSession, factory: AsyncAppRepositoryFactory) -> None:
        super().__init__(Order, session, factory)

    async def count_for_user(self, user_id: PrimaryKey, *, status: str | None = None) -> int:
        filters: dict[str, object] = {"user_id": user_id}
        if status is not None:
            filters["status"] = status
        return await self.count(**filters)

    async def orders_for_user(self, user_id: PrimaryKey) -> list[Order]:
        return list(await self.filter(user_id=user_id))
```

Implement `AsyncSessionRepositoryFactory` the same way as sync, using `AsyncSqlAlchemyStatementBuilder` and `AsyncBaseRepository`.

---

## Protocols for service-layer typing

Use sqlphilosophy protocols when a service should depend on **capabilities**, not a concrete subclass:

```python
from sqlphilosophy.aio.protocols import AsyncBaseRepositoryProtocol, AsyncRepositoryFactory
from sqlphilosophy.sync.protocols import BaseRepositoryProtocol, RepositoryFactory


def sync_user_count(repo: BaseRepositoryProtocol[User, RepositoryFactory | None]) -> int:
    return repo.count(is_active=True)


async def async_user_count(repo: AsyncBaseRepositoryProtocol[User, AsyncRepositoryFactory | None]) -> int:
    return await repo.count(is_active=True)


def load_users(factory: AppRepositoryFactory) -> list[User]:
    return factory.users().active_users()
```

Protocols are especially useful for:

- Unit tests (fake repos implementing the protocol).
- Services that accept any `User`-scoped repository.
- Typing `factory.repository(User)` return values without importing your concrete `UserRepository`.

Import from explicit submodules:

- `sqlphilosophy.sync.protocols`
- `sqlphilosophy.aio.protocols`

---

## Typing aliases in method signatures

```python
from sqlphilosophy.types import OrmModel, PrimaryKey, RowMapping, RowValue, SqlBindParams, SqlFilter


def deactivate_user(repo: UserRepository, user_id: PrimaryKey) -> int:
    return repo.update_partial(user_id, {"is_active": False}, frozenset({"is_active"}))


def export_active_emails(repo: UserRepository) -> list[RowMapping]:
    rows, _total = repo.search_page(ListQuery.from_page(page=1, size=100))
    return rows


def pending_orders_stmt(user_id: PrimaryKey) -> tuple[list[SqlFilter], SqlBindParams]:
    criteria: list[SqlFilter] = [Order.user_id == user_id, Order.status == "pending"]
    params: SqlBindParams = {}
    return criteria, params


def repo_for_model(factory: AppRepositoryFactory, model: OrmModel) -> BaseRepository:
    return factory.repository(model)


def apply_lookup(repo: UserRepository, **filters: RowValue) -> User | None:
    return repo.first(**filters)
```

---

## Service-layer examples

### Sync

```python
class UserService:
    def __init__(self, factory: AppRepositoryFactory) -> None:
        self._factory = factory

    def register(self, email: str, display_name: str) -> User:
        users = self._factory.users()
        user, created = users.get_or_create(defaults={"display_name": display_name}, email=email)
        if created:
            users._session.commit()
        return user

    def active_directory(self, page: int, size: int) -> tuple[list[RowMapping], int]:
        query = ListQuery.from_page(page=page, size=size, order_by={"email": "asc"})
        return self._factory.users().search_page(query)

    def user_pending_orders(self, user_id: PrimaryKey) -> int:
        return self._factory.users().pending_order_count(user_id)
```

### Async

```python
class AsyncUserService:
    def __init__(self, factory: AsyncAppRepositoryFactory) -> None:
        self._factory = factory

    async def register(self, email: str, display_name: str) -> User:
        users = self._factory.users()
        user, created = await users.get_or_create(defaults={"display_name": display_name}, email=email)
        if created:
            await users._session.commit()
        return user

    async def active_directory(self, page: int, size: int) -> tuple[list[RowMapping], int]:
        query = ListQuery.from_page(page=page, size=size)
        return await self._factory.users().search_page(query)
```

Services own **authorization**, **commit/rollback**, and orchestration. Repositories expose typed data access.

---

## Cross-repository workflows

### User repository → order repository

```python
# sync
users = factory.users()
pending = users.pending_order_count(user_id=42)
orders = users.for_repo(OrderRepository).orders_for_user(42)

# async
users = factory.users()
pending = await users.pending_order_count(user_id=42)
orders = await users.for_repo(AsyncOrderRepository).orders_for_user(42)
```

### Order repository scoped to a user

```python
# sync
order_repo = factory.orders()
pending = order_repo.list_for_user(
    user_id=42,
    criteria=[Order.status == "pending"],
)

# async
order_repo = factory.orders()
pending = await order_repo.statement().where(Order.user_id == 42, Order.status == "pending").scalars().all()
```

`for_repo()` requires the repository was constructed **with a factory**; otherwise it raises `FactoryRequiredError` from `servicephilosophy`.

---

## Typed query builder methods

Domain methods can return entities, mappings, or paginated tuples:

```python
# ORM entities
def active_users(self) -> list[User]:
    return self.statement().where(User.is_active.is_(True)).scalars().all()

# Row mappings
def email_rows(self) -> list[RowMapping]:
    return self.statement().select_columns(User.id, User.email).mappings().all()

# Paginated mappings + total (tuple unpacking)
def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
    sort = SortConfig(default=SortSpec("email", "asc"), columns={...})
    return self.statement().fetch_page(query, sort=sort)

# Async — prefix terminals with await
async def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
    return await self.statement().fetch_page(query, sort=sort)
```

`fetch_page` returns `(rows, total)` and does **not** mutate the builder.

---

## Recommended app structure

```
myapp/
  models/
    user.py
    order.py
  repositories/
    factory.py              # SessionRepositoryFactory / AsyncSessionRepositoryFactory
    user_repository.py      # UserRepository / AsyncUserRepository
    order_repository.py     # OrderRepository / AsyncOrderRepository
  services/
    user_service.py         # commits, authorization, orchestration
```

- **sqlphilosophy** — `BaseRepository`, builders, sorting, SQL helpers, protocols.
- **Your app** — models, typed repos, factory, services, migrations, auth.

Wire the factory once per request/task:

```python
with SessionLocal() as session:
    factory = SessionRepositoryFactory(session)
    service = UserService(factory)
    ...
    session.commit()
```

---

## Common mistakes

| Mistake | Why it fails |
|---------|----------------|
| Repository without a session | Repositories must wrap a live `Session` / `AsyncSession`. |
| `commit()` inside normal repo methods | Breaks transaction ownership; caller should commit (except `batched_purge_ids`). |
| Authorization inside base repositories | sqlphilosophy does not enforce access control — check in services. |
| User input as SQL identifiers | Use bind params for values; identifiers only from trusted allowlists ([trusted-sql.md](./trusted-sql.md)). |
| `from sqlphilosophy import BaseRepository` | Root package exports only `__version__`; import explicit submodules. |
| `for_repo()` without factory | Pass factory to `BaseRepository(model, session, factory)`; missing factory raises `FactoryRequiredError`. |
| Ignoring `writable` on partial updates | Always allowlist patchable fields in application code. |

---

## See also

- [typed-repositories.md](./typed-repositories.md) — shorter overview
- [query-builder.md](./query-builder.md) · [sorting-pagination.md](./sorting-pagination.md)
- [types-version.md](./types-version.md) — full alias list
- Runnable: [typed_repository_sync.py](../examples/typed_repository_sync.py), [typed_repository_async.py](../examples/typed_repository_async.py)
