# sqlphilosophy

Portable SQLAlchemy repository kit for typed CRUD, fluent statement building, sort/pagination, and Core SQL helpers — with explicit sync and async session APIs.

| | |
|---|---|
| **PyPI** | [`sqlphilosophy`](https://pypi.org/project/sqlphilosophy/) |
| **GitHub** | [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy) |
| **Import** | `sqlphilosophy` (no root reexports — use explicit submodules below) |

Developed in the [DeliveryPlus](https://github.com/SignalSafeSoftware/DeliveryPlus) monorepo under `libs/sqlphilosophy`; this tree is the publishable package source.

## Install

```bash
pip install sqlphilosophy
```

Async ORM (`AsyncSession`) also needs greenlet:

```bash
pip install sqlphilosophy[async]
```

Requires Python 3.12+ and SQLAlchemy 2.x.

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

# Without a factory — statement() returns SqlAlchemyStatementBuilder directly
repo = BaseRepository(User, session)
rows = repo.statement().where(User.active.is_(True)).mappings().all()

# With a factory — statement() and for_repo() delegate to the factory
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

## Audit mixins

```python
from sqlphilosophy.audit.context import audit_context
from sqlphilosophy.audit.listener import configure_audit_listeners
from sqlphilosophy.audit.model import TimestampModel

configure_audit_listeners()

with audit_context(actor_id=42):
    session.add(MyModel(name="example"))
    session.flush()
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
twine check dist/*
```

## Releasing

See [RELEASING.md](./RELEASING.md) for GitHub + PyPI trusted publishing.

## License

MIT — see [LICENSE](./LICENSE).
