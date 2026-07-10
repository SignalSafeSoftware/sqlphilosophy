# Typed repositories and factories

[← Repository guide](../repository-guide.md) · [Strongly typed guide](./strongly-typed-repositories.md) · [Setup](./setup.md)

Subclass repositories for domain methods; use a session-scoped factory to cache repos and share `statement()` builders.

## Layering with servicePhilosophy

```text
ServiceRepository[FactoryT] is a neutral factory-aware base.
It does not require a model.
BaseRepository[ModelT, FactoryT] remains the SQL/model-backed specialization.
```

`BaseRepository[ModelT, FactoryT]` extends `ServiceRepository[FactoryT]` from [`servicephilosophy`](https://github.com/SignalSafeSoftware/servicephilosophy). The SQL layer requires a model and session; `ServiceRepository` alone does not.

Repositories inherit `.factory`, `.maybe_factory`, and `.has_factory`. Accessing `.factory` or calling `for_repo()` without a configured factory raises `FactoryRequiredError`.

Business logic with no ORM model can live in a `ServiceRepository` subclass:

```python
from servicephilosophy import ServiceRepository


class PermissionService(ServiceRepository[ServiceFactory]):
    def can_view(self, user_id: int, resource_id: int) -> bool:
        return self.factory.repositories.users().exists(user_id)
```

**In-depth guide:** [strongly-typed-repositories.md](./strongly-typed-repositories.md)

**Composition root (`ServiceFactory` + `.repositories` / `.services`):** [service-factory-composition.md](./service-factory-composition.md)

**Full runnable examples:**

- [docs/examples/typed_repository_sync.py](../examples/typed_repository_sync.py)
- [docs/examples/typed_repository_async.py](../examples/typed_repository_async.py)

---

## Subclassing `BaseRepository`

```python
from sqlalchemy.orm import Session

from sqlphilosophy.sync.repository import BaseRepository


class UserRepository(BaseRepository[User, "AppFactory"]):
    def __init__(self, session: Session, factory: AppFactory) -> None:
        super().__init__(User, session, factory)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def active_count(self) -> int:
        return self.count(is_active=True)
```

## Subclassing `AsyncBaseRepository`

```python
from sqlalchemy.ext.asyncio import AsyncSession

from sqlphilosophy.aio.repository import AsyncBaseRepository


class UserRepository(AsyncBaseRepository[User, "AppFactory"]):
    def __init__(self, session: AsyncSession, factory: AppFactory) -> None:
        super().__init__(User, session, factory)

    async def get_by_email(self, email: str) -> User | None:
        return await self.first(email=email)
```

## Factory protocol and caching

Implement `RepositoryFactory` / `AsyncRepositoryFactory`:

- `create_statement(model)` → builder
- `get_repository(RepoClass)` → cached typed repo
- `repository(model)` → generic CRUD repo

See the typed examples for `SessionRepositoryFactory` with a `dict` cache per session.

## `for_repo` — cross-repository usage

Requires a factory on the repository. Without one, `for_repo()` raises `FactoryRequiredError` from `servicephilosophy`.

```python
# sync
users = factory.users()
company_repo = users.for_repo(CompanyRepository)
orders = users.for_repo(OrderRepository)

# async
users = factory.users()
orders = await users.for_repo(OrderRepository).filter(page=1, limit=10, user_id=1)
```

**Next:** [strongly-typed-repositories.md](./strongly-typed-repositories.md) · [reads.md](./reads.md) · [query-builder.md](./query-builder.md)
