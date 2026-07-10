# Setup and shared models

[← Repository guide](../repository-guide.md)

Start here for example models and session/repository setup. Other usage pages assume these patterns.

---

## Shared example models

Examples use compact models with a foreign-key relationship. **Your app owns engine, session factory, and migrations.**

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

Throughout the usage guide:

```python
user_repo = BaseRepository(User, session)          # sync
order_repo = BaseRepository(Order, session)

# async equivalents:
# user_repo = AsyncBaseRepository(User, session)
# order_repo = AsyncBaseRepository(Order, session)
```

---

## Sync setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from sqlphilosophy.sync.repository import BaseRepository

engine = create_engine("sqlite:///:memory:", future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

with SessionLocal() as session:
    user_repo = BaseRepository(User, session)

    alice = user_repo.create(email="alice@example.com", display_name="Alice")
    # create → add → flush; PK available, transaction still open

    session.commit()  # persist the unit of work

    user = user_repo.get(alice.id)
    user_repo.update_partial(user.id, {"display_name": "Alice K."}, writable=frozenset({"display_name"}))
    session.commit()
```

**When to commit:** after a logical unit of work (HTTP request handler, CLI command, message consumer). The repository never commits for normal CRUD.

See [writes.md](./writes.md) for create/update patterns and [deletes.md](./deletes.md) for destructive operations.

---

## Async setup

```python
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlphilosophy.aio.repository import AsyncBaseRepository

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
# await conn.run_sync(Base.metadata.create_all) during app startup
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def create_user(session: AsyncSession) -> User:
    user_repo = AsyncBaseRepository(User, session)
    user = await user_repo.create(email="bob@example.com", display_name="Bob")
    await session.commit()
    return user


async def main() -> None:
    async with session_factory() as session:
        user = await create_user(session)
        user_repo = AsyncBaseRepository(User, session)
        loaded = await user_repo.get(user.id)
        await user_repo.update_partial(loaded.id, {"is_active": False}, writable=frozenset({"is_active"}))
        await session.commit()
```

Mirror sync lifecycle with `await` on repository and builder terminal methods.

---

## Package install and local development

`sqlphilosophy` declares [`servicephilosophy`](https://github.com/SignalSafeSoftware/servicephilosophy) as a normal PyPI dependency (`servicephilosophy>=0.1.0`). A fresh clone needs only this repository:

```bash
uv sync --all-extras
```

### Editable `servicephilosophy` (optional, local only)

When developing both packages side by side, install the sibling checkout into your virtual environment without committing a path override to `pyproject.toml`:

```bash
uv pip install -e ../servicephilosophy
```

Alternatively, add a **temporary** local override in `pyproject.toml` (do not commit):

```toml
[tool.uv.sources]
servicephilosophy = { path = "../servicephilosophy", editable = true }
```

Run `uv lock` after adding or removing that block. CI and other clones resolve `servicephilosophy` from PyPI.

**Next:** [reads.md](./reads.md) · [writes.md](./writes.md)
