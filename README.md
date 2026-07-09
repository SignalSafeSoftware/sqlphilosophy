# sqlphilosophy

Portable SQLAlchemy repository kit: sync and async CRUD, fluent statement builders, sort/pagination, Core SQL helpers, and optional audit listeners.

| | |
|---|---|
| **PyPI** | [`sqlphilosophy`](https://pypi.org/project/sqlphilosophy/) |
| **GitHub** | [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy) |
| **Import** | `sqlphilosophy` (explicit submodules — no root re-exports) |
| **Python** | 3.12+ |
| **License** | MIT — see [LICENSE](./LICENSE) |

## What this package does

- **Repository pattern** for a single mapped model (`BaseRepository`, `AsyncBaseRepository`).
- **Fluent query builders** with pagination/sort (`StatementQueryBuilder`, `ListQuery`, `SortConfig`).
- **SQL helpers** for row mapping, partial updates, filters, and developer-defined raw SQL fragments.
- **Optional audit listeners** and timestamp mixins.

## What this package does not do

- Migrations, schema design, or connection pooling configuration.
- Authorization, multi-tenant isolation, or query sandboxing.
- Automatic commits for normal CRUD — see [Transaction ownership](#transaction-ownership) below.

## Install

```bash
pip install sqlphilosophy
```

Async ORM (`AsyncSession`) also needs greenlet:

```bash
pip install sqlphilosophy[async]
```

Requires Python 3.12+ and SQLAlchemy 2.x.

## Full example (sync model + session)

```python
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.repository import BaseRepository


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widget"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


engine = create_engine("sqlite:///:memory:", future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

with SessionLocal() as session:
    repo = BaseRepository(Widget, session)
    widget = repo.create(name="alpha")  # stages + flush; does not commit
    session.commit()

    page = repo.statement().fetch_page(ListQuery.from_page(page=1, size=20))
    assert page.total >= 1
```

**Async:** swap `Session` → `AsyncSession`, `BaseRepository` → `AsyncBaseRepository` from `sqlphilosophy.aio.repository`, and `await` repository methods.

## Strongly typed repositories (factory pattern)

Domain repositories subclass `BaseRepository[Model, RepositoryFactory]` (or `AsyncBaseRepository` for async) and add typed query helpers. A session-scoped factory implements `RepositoryFactory` to cache repositories and wire `statement()` / `for_repo()` across repos on the same session.

```python
from sqlalchemy.orm import Session

from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.repository import BaseRepository


class UserRepository(BaseRepository[User, RepositoryFactory]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def get_by_username(self, username: str) -> User | None:
        return self.first(username=username)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def get_active_by_email(self, email: str) -> User | None:
        return (
            self.statement()
            .where(User.email == email, User.is_active.is_(True))
            .scalars()
            .first()
        )
```

Full runnable examples with models, a multi-repo factory, and cross-repository usage:

- Sync: [`examples/typed_repository_sync.py`](./examples/typed_repository_sync.py)
- Async: [`examples/typed_repository_async.py`](./examples/typed_repository_async.py)

For async, swap `Session` → `AsyncSession`, `BaseRepository` → `AsyncBaseRepository` from `sqlphilosophy.aio.repository`, and `await` repository methods.

## Package layout

| Module | Contents |
|--------|----------|
| `sqlphilosophy.types` | Portable typing aliases (`RowMapping`, `PrimaryKey`, `SqlFilter`, …) |
| `sqlphilosophy.sql` | Row mapping helpers, partial updates, Core table helpers, filter builders |
| `sqlphilosophy.sorting` | `ListQuery`, `SortConfig`, `SortSpec`, pagination/sort resolution |
| `sqlphilosophy.sync` | Sync `BaseRepository`, `StatementQueryBuilder`, `RepositoryFactory` protocol |
| `sqlphilosophy.aio` | Async `AsyncBaseRepository`, `AsyncStatementQueryBuilder`, `AsyncRepositoryFactory` |
| `sqlphilosophy.audit` | Optional SQLAlchemy audit listeners and timestamp mixins |

## Sync usage

```python
from sqlalchemy.orm import Session

from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sql import partial_update_model, row_int
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder

repo = BaseRepository(User, session)
rows = repo.statement().where(User.active.is_(True)).mappings().all()

repo = BaseRepository(User, session, factory)
page = repo.statement().fetch_page(ListQuery.from_page(page=1, size=20))
other = repo.for_repo(OrderRepository)
```

## Async usage

```python
from sqlalchemy.ext.asyncio import AsyncSession

from sqlphilosophy.aio.repository import AsyncBaseRepository

repo = AsyncBaseRepository(User, session)
rows = await repo.statement().where(User.active.is_(True)).mappings().all()
```

## Transaction ownership

- **`create` / `update` / `delete` helpers** on repositories call `session.flush()` but **do not commit** unless documented otherwise.
- **`delete_all()`** executes a bulk delete and **does not commit** — the caller owns `session.commit()` / `rollback()` for the work unit.
- **`batched_purge_ids(...)`** deletes matching rows in batches and **commits after each batch** — treat it as a destructive, application-level operation you must authorize first.
- Your application owns **`session.commit()` / `rollback()`** for normal request/work-unit boundaries.

## Raw SQL trust boundaries

The following must be **developer-defined** and must **never** be built from end-user input:

- Raw SQL fragments passed to SQL helper functions
- Literal column names, table names, and `ORDER BY` expressions
- Sort field allowlists wired into query builders

**User-supplied values must use bind parameters** (SQLAlchemy bound values), not string concatenation into SQL text or identifiers. See [SECURITY.md](./SECURITY.md).

## Destructive helpers

- **`delete_all()`** — removes all rows for the repository model (sync and async variants). Does **not** commit; caller must commit or roll back.
- **`batched_purge_ids(...)`** — deletes matching rows in batches and commits each batch.

Call only after your application has authorized the operation. These helpers assume the caller understands the data loss impact.

## Audit mixins

```python
from sqlphilosophy.audit.context import audit_context
from sqlphilosophy.audit.listener import configure_audit_listeners
from sqlphilosophy.audit.model import TimestampModel

configure_audit_listeners()

with audit_context(actor_id=42):
    session.add(MyModel(name="example"))
    session.flush()
    session.commit()
```

Audit listeners record changes; they do **not** enforce access control.

## Development

This repo uses [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
uv run pytest
uv run flake8 .
uv run python -m build
```

## Security

See [SECURITY.md](./SECURITY.md) for vulnerability reporting and SQL trust boundaries.

## Releasing

See [RELEASING.md](./RELEASING.md) for GitHub + PyPI trusted publishing. See [CHANGELOG.md](./CHANGELOG.md).

## License

MIT — see [LICENSE](./LICENSE).
