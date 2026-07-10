# sqlphilosophy

Portable SQLAlchemy repository kit: sync and async CRUD, fluent statement builders, sort/pagination, Core SQL helpers, and optional audit listeners.

| | |
|---|---|
| **PyPI** | [`sqlphilosophy`](https://pypi.org/project/sqlphilosophy/) |
| **GitHub** | [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy) |
| **Import** | `sqlphilosophy` (`__version__` only) — use explicit submodules for APIs |
| **Python** | 3.12+ |
| **License** | MIT — see [LICENSE](./LICENSE) |

## Documentation

| Resource | Description |
|----------|-------------|
| [Repository guide](./docs/repository-guide.md) | Entry point: overview, transaction model, links to usage pages |
| [Usage examples](./docs/usage/) | Focused sync/async code examples by feature area |
| [Strongly typed repositories](./docs/usage/strongly-typed-repositories.md) | Typed subclasses, factories, protocols, and service patterns |
| [Service factory composition](./docs/usage/service-factory-composition.md) | Compose sqlPhilosophy SQL repos with servicePhilosophy business services |
| [Before/after SQLAlchemy](./docs/usage/before-after-sqlalchemy.md) | Migration examples: direct SQLAlchemy vs repository-centered code |
| [Feature matrix](./docs/feature-matrix.md) | Full sync/async capability map |
| [Typed repository (sync)](./docs/examples/typed_repository_sync.py) | Runnable factory + domain repo example |
| [Typed repository (async)](./docs/examples/typed_repository_async.py) | Async counterpart |

## What this package does

- **Repository pattern** for a single mapped model (`BaseRepository`, `AsyncBaseRepository`).
- **Fluent query builders** with pagination/sort (`StatementQueryBuilder`, `ListQuery`, `SortConfig`).
- **SQL helpers** for row mapping, partial updates, and developer-defined fragments via **`sqlphilosophy.trusted_sql`**.
- **Optional audit listeners** and timestamp mixins.

## What this package does not do

- Migrations, schema design, or connection pooling configuration.
- Authorization, multi-tenant isolation, or query sandboxing.
- Automatic commits for normal CRUD — see [Transaction ownership](#transaction-ownership).

## Install

```bash
pip install sqlphilosophy
```

Async ORM (`AsyncSession`) also needs greenlet:

```bash
pip install sqlphilosophy[async]
```

Requires Python 3.12+ and SQLAlchemy 2.x.

## Quick start (sync)

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
    repo.create(name="alpha")  # stages + flush; does not commit
    session.commit()

    rows, total = repo.statement().fetch_page(ListQuery.from_page(page=1, size=20))
    assert total >= 1
```

**Async:** use `AsyncSession`, `AsyncBaseRepository` from `sqlphilosophy.aio.repository`, and `await` on repository/builder terminals. See the [repository guide](./docs/repository-guide.md).

## Package layout

| Module | Contents |
|--------|----------|
| `sqlphilosophy` | `__version__` only |
| `sqlphilosophy.types` | Portable typing aliases |
| `sqlphilosophy.sql` | Row mapping, partial updates, Core helpers (re-exports `trusted_sql`) |
| `sqlphilosophy.trusted_sql` | Developer-trusted SQL fragments — see [SECURITY.md](./SECURITY.md) |
| `sqlphilosophy.sorting` | `ListQuery`, `SortConfig`, `SortSpec` |
| `sqlphilosophy.sync` / `sqlphilosophy.aio` | Repositories, query builders, factory protocols |
| `sqlphilosophy.audit` | Optional listeners and timestamp mixins |

## Transaction ownership

- **`create` / `add` / `update_partial` / `remove` / `delete_*` / `update_where`** — flush or execute DML; **caller commits**.
- **`delete_all()`** — bulk delete; **does not commit**.
- **`batched_purge_ids(..., batch_size=...)`** — deletes in batches and **commits after each batch**; requires **`batch_size >= 1`**. Authorize in application code first.

## Raw SQL trust boundaries

Identifiers and SQL fragments (table/column names, `ORDER BY` text, sort allowlists) must be **developer-defined**, never built from end-user input. User **values** use bind parameters.

Import trusted helpers from **`sqlphilosophy.trusted_sql`** (`sql_table`, `col_eq`, `col_icontains`, `col_range`, `literal_order_expr`, …). The same names are re-exported from `sqlphilosophy.sql`. Details: [SECURITY.md](./SECURITY.md) and the [repository guide](./docs/repository-guide.md).

## Development

This repo uses [uv](https://docs.astral.sh/uv/) and [Ruff](https://docs.astral.sh/ruff/):

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests docs/examples
uv run ruff format src tests docs/examples

# Optional: validate runnable docs examples (SQLite in-memory; CI runs these in smoke-package)
uv run --extra dev python docs/examples/typed_repository_sync.py
uv run --extra dev python docs/examples/typed_repository_async.py

uv run python -m build
```

## Security

See [SECURITY.md](./SECURITY.md) for vulnerability reporting and SQL trust boundaries.

## Releasing

See [RELEASING.md](./RELEASING.md) for GitHub + PyPI trusted publishing. See [CHANGELOG.md](./CHANGELOG.md).

## License

MIT — see [LICENSE](./LICENSE).
