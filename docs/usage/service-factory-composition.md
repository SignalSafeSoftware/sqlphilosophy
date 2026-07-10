# Composing sqlPhilosophy with servicePhilosophy

[← Repository guide](../repository-guide.md) · [Typed repositories](./typed-repositories.md) · [servicePhilosophy integration](../integration/servicephilosophy.md)

This page shows how an **application** wires together two layers:

| Layer | Package | Role |
| ----- | ------- | ---- |
| Factory-aware base | [servicePhilosophy](https://github.com/SignalSafeSoftware/servicephilosophy) | Optional factory wiring; **no model, SQL, or HTTP** |
| SQL persistence | sqlPhilosophy | Model-bound repositories (`BaseRepository`) |
| Business logic | *your application* | Service repositories (`ServiceRepository` subclasses) |

Install both packages:

```bash
pip install sqlphilosophy servicephilosophy
```

---

## Architecture

One request-scoped (or unit-of-work-scoped) **`ServiceFactory`** exposes two namespaces:

```text
ServiceFactory
  .repositories -> sqlPhilosophy repository factory  (database)
  .services     -> app business service repositories (domain logic)
```

```text
                 ServiceFactory
                /              \
   RepositoryFactory    ServiceRepositoryFactory
   (sqlPhilosophy)      (application)
          |                      |
   UserRepository      PermissionServiceRepository
   (User ORM model)     (no model)
```

- **`factory.repositories`** — typed SQL repos, session-scoped, cached by your `RepositoryFactory`.
- **`factory.services`** — business rules that compose SQL repos (and, later, API clients or other sources).

---

## Complete minimal example (sync)

The following is a self-contained sketch you can adapt in your app. It uses a JSON `roles` column so `has_role` can check membership without extra tables.

```python
from __future__ import annotations

from typing import Any, cast

from servicephilosophy import ServiceRepository
from sqlalchemy import JSON, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository


# --- ORM model (persistence) ---


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)


# --- SQL repository (thin persistence; no business rules) ---


class UserRepository(BaseRepository[User, RepositoryFactory]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)


# --- Business service repository (no model) ---


class PermissionServiceRepository(ServiceRepository[ServiceFactory]):
    def has_role(self, user_id: int, role: str) -> bool:
        user = self.factory.repositories.users().get(user_id)
        return role in user.roles


# --- Namespace factories ---


class ServiceRepositoryFactory:
    def __init__(self, factory: ServiceFactory) -> None:
        self._factory = factory
        self._cache: dict[type[ServiceRepository[Any]], ServiceRepository[Any]] = {}

    def permissions(self) -> PermissionServiceRepository:
        return self._cached(PermissionServiceRepository)

    def _cached[R: ServiceRepository[Any]](self, repo_class: type[R]) -> R:
        cached = self._cache.get(repo_class)
        if cached is None:
            cached = repo_class(self._factory)
            self._cache[repo_class] = cached
        return cast(R, cached)


class RepositoryFactory:
    """sqlPhilosophy-facing factory: statement builders + typed SQL repos."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._root: ServiceFactory | None = None
        self._repositories: dict[type[Any], BaseRepository[Any, RepositoryFactory]] = {}

    def attach(self, root: ServiceFactory) -> None:
        """Called once from ``ServiceFactory`` so SQL repos can reach sibling namespaces."""
        self._root = root

    def create_statement(self, model: type[User]) -> StatementQueryBuilder[User]:
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type[UserRepository]) -> UserRepository:
        cached = self._repositories.get(repo_class)
        if cached is None:
            cached = repo_class(self._session, self)
            self._repositories[repo_class] = cached
        return cast(UserRepository, cached)

    def repository(self, model: type[User]) -> BaseRepository[User, RepositoryFactory]:
        return BaseRepository(model, self._session, self)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)


class ServiceFactory:
    def __init__(self, repositories: RepositoryFactory) -> None:
        self.repositories = repositories
        self.services = ServiceRepositoryFactory(self)
        repositories.attach(self)


# --- Usage ---


engine = create_engine("sqlite:///:memory:", future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

with SessionLocal() as session:
    repositories = RepositoryFactory(session)
    factory = ServiceFactory(repositories)

    admin = factory.repositories.users().create(
        email="admin@example.com",
        roles=["admin", "viewer"],
    )
    session.commit()

    assert factory.services.permissions().has_role(admin.id, "admin") is True
    assert factory.services.permissions().has_role(admin.id, "editor") is False
```

Your `RepositoryFactory` should implement the sqlPhilosophy factory surface (`create_statement`, `get_repository`, `repository`) in addition to typed accessors like `users()`. See [typed_repository_sync.py](../examples/typed_repository_sync.py) for a fuller caching pattern.

---

## Usage in a handler

Construct one `ServiceFactory` per request or unit of work, then call the namespace that matches the concern:

```python
def handle_get_profile(session: Session, user_id: int) -> dict[str, object]:
    factory = ServiceFactory(RepositoryFactory(session))

    user = factory.repositories.users().get(user_id)
    is_admin = factory.services.permissions().has_role(user_id, "admin")

    return {"email": user.email, "is_admin": is_admin}
```

Typical flow:

1. **Handler** obtains a SQLAlchemy session.
2. **`ServiceFactory`** is created once for that scope.
3. **Service repositories** implement use-case methods and delegate persistence to `.repositories`.
4. **SQL repositories** stay thin — queries, CRUD, and mapping only.

---

## Layer responsibilities

| Class | Extends | Has `model`? | Responsibility |
| ----- | ------- | ------------ | -------------- |
| `UserRepository` | `BaseRepository[User, RepositoryFactory]` | Yes — SQLAlchemy `User` | Load/save rows, typed queries |
| `PermissionServiceRepository` | `ServiceRepository[ServiceFactory]` | **No** | Role checks, permission rules, orchestration |
| `RepositoryFactory` | (app class; implements sqlPhilosophy factory protocol) | — | Cache SQL repos, expose `create_statement` |
| `ServiceFactory` | (app class) | — | Composition root for `.repositories` and `.services` |

### `PermissionServiceRepository` has no model

It is **not** a sqlPhilosophy repository. It does not take a mapped class or `Session`. It only receives the root `ServiceFactory` and reaches SQL through `self.factory.repositories`.

### `UserRepository` remains SQL/model-backed

It inherits from `BaseRepository`, which adds `model`, `_session`, CRUD, and `statement()`. Domain-specific **queries** belong here (`get_by_email`, filters, joins). **Business rules** (for example “can this actor perform this action?”) belong in service repositories.

### `ServiceRepository` only provides factory access

From [servicePhilosophy](https://github.com/SignalSafeSoftware/servicephilosophy), the base exposes:

- `.factory` — required factory reference (`FactoryRequiredError` if missing)
- `.maybe_factory` / `.has_factory` — optional wiring

It does not define SQL methods, HTTP clients, or ORM models. Your subclass adds the business API (`has_role`, `onboard_user`, …).

### Keep business logic out of SQL CRUD repositories

| Put here | Not here |
| -------- | -------- |
| `UserRepository.get_by_email` | `UserRepository.has_role` |
| `PermissionServiceRepository.has_role` | `BaseRepository` subclass with permission rules |
| Cross-repo orchestration in service repos | Fat SQL repos that encode product policy |

If a method needs **multiple models**, **external APIs**, or **policy**, implement it on a `ServiceRepository` and call `self.factory.repositories…` (or `.services…`) from there.

---

## Async variant

The same shape applies with `AsyncBaseRepository`, `AsyncSession`, and `AsyncRepositoryFactory` from `sqlphilosophy.aio`. Service repositories stay synchronous factory holders unless they perform I/O — then make service methods `async` and `await` async SQL repos.

---

## Related docs

- [Integration notes](../integration/servicephilosophy.md) — adoption checklist and protocol layering
- [Typed repositories](./typed-repositories.md) — subclassing and factory protocols
- [Strongly typed repositories](./strongly-typed-repositories.md) — layouts, cross-repo `for_repo`, mistakes
- [Runnable SQL factory demo](../examples/typed_repository_sync.py)
- [servicePhilosophy — three-layer composition](https://github.com/SignalSafeSoftware/servicephilosophy/blob/main/docs/examples/service-factory-composition.md) — adds a proposed API layer alongside SQL and services
