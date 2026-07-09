"""Async strongly typed domain repositories with a session-scoped factory.

Run from the repo root::

    uv run --extra dev python docs/examples/typed_repository_async.py
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, cast

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import sqlphilosophy
from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder, AsyncStatementQueryBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.types import PrimaryKey, RowMapping

T = TypeVar("T", bound=DeclarativeBase)
U = TypeVar("U", bound='AsyncBaseRepository[T, "AppRepositoryFactory"]')  # type: ignore[valid-type]


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    users: Mapped[list[User]] = relationship(back_populates="company")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    company: Mapped[Company] = relationship(back_populates="users")
    orders: Mapped[list[Order]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "order"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    user: Mapped[User] = relationship(back_populates="orders")


class UserRepository(AsyncBaseRepository[User, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``User``."""

    def __init__(self, session: AsyncSession, factory: AppRepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def _app_factory(self) -> AppRepositoryFactory:
        if self._factory is None:
            raise RuntimeError("AppRepositoryFactory is required")
        return cast(AppRepositoryFactory, self._factory)

    async def get_by_email(self, email: str) -> User | None:
        return await self.first(email=email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.first(username=username)

    async def active_users(self) -> list[User]:
        return list(await self.filter(is_active=True))

    async def list_for_company(self, company_id: int) -> list[User]:
        return list(await self.filter(company_id=company_id))

    async def get_active_by_email(self, email: str) -> User | None:
        return await self.statement().where(User.email == email, User.is_active.is_(True)).scalars().first()

    async def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
        sort = SortConfig(
            default=SortSpec("email", "asc"),
            columns={
                "email": {"asc": User.email, "desc": User.email.desc()},
                "username": {"asc": User.username, "desc": User.username.desc()},
            },
        )
        return await self.statement().where(User.is_active.is_(True)).fetch_page(query, sort=sort)

    async def pending_order_count(self, user_id: PrimaryKey) -> int:
        return await self.for_repo(OrderRepository).count_for_user(user_id, status="pending")


class OrderRepository(AsyncBaseRepository[Order, "AppRepositoryFactory"]):
    """Domain repository for ``Order`` rows."""

    def __init__(self, session: AsyncSession, factory: AppRepositoryFactory) -> None:
        super().__init__(Order, session, factory)

    async def count_for_user(self, user_id: PrimaryKey, *, status: str | None = None) -> int:
        filters: dict[str, object] = {"user_id": user_id}
        if status is not None:
            filters["status"] = status
        return await self.count(**filters)

    async def orders_for_user(self, user_id: PrimaryKey) -> list[Order]:
        return list(await self.filter(user_id=user_id))


class CompanyRepository(AsyncBaseRepository[Company, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``Company``."""

    def __init__(self, session: AsyncSession, factory: AppRepositoryFactory) -> None:
        super().__init__(Company, session, factory)

    def _app_factory(self) -> AppRepositoryFactory:
        if self._factory is None:
            raise RuntimeError("AppRepositoryFactory is required")
        return cast(AppRepositoryFactory, self._factory)

    async def get_by_slug(self, slug: str) -> Company | None:
        return await self.first(slug=slug)

    async def get_by_name(self, name: str) -> Company | None:
        return await self.first(name=name)

    async def list_users(self, company_id: int) -> list[User]:
        return await self._app_factory().users().list_for_company(company_id)

    async def count_users(self, company_id: int) -> int:
        return await self._app_factory().users().count(company_id=company_id)


class AppRepositoryFactory(AsyncRepositoryFactory, Protocol):
    """App-specific factory surface: typed repos plus sqlphilosophy factory methods."""

    def companies(self) -> CompanyRepository: ...

    def users(self) -> UserRepository: ...

    def orders(self) -> OrderRepository: ...


class AsyncSessionRepositoryFactory:
    """Session-scoped factory implementing ``AppRepositoryFactory``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repositories: dict[Any, Any] = {}

    def create_statement(self, model: type[T]) -> AsyncStatementQueryBuilder[T]:
        return AsyncSqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type[U]) -> U:
        cached = self._repositories.get(repo_class)
        if cached is None:
            constructor = cast(
                Callable[[AsyncSession, AppRepositoryFactory], U],
                repo_class,
            )
            cached = constructor(self._session, cast(AppRepositoryFactory, self))
            self._repositories[repo_class] = cached
        return cast(U, cached)

    def repository(self, model: type[T]) -> AsyncBaseRepository[T, AppRepositoryFactory]:
        return AsyncBaseRepository(model, self._session, cast(AppRepositoryFactory, self))

    def companies(self) -> CompanyRepository:
        return self.get_repository(CompanyRepository)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)

    def orders(self) -> OrderRepository:
        return self.get_repository(OrderRepository)


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        factory = AsyncSessionRepositoryFactory(session)

        companies = factory.companies()
        acme = await companies.create(name="Acme", slug="acme-comp")
        abc = await companies.create(name="ABC", slug="abc-comp")
        await session.flush()

        users = factory.users()
        alice = await users.create(
            username="alice",
            email="alice@acme.com",
            is_active=True,
            company_id=acme.id,
        )
        await users.create(
            username="bob",
            email="bob@abc.com",
            is_active=False,
            company_id=abc.id,
        )
        await session.flush()

        orders = factory.orders()
        await orders.create(user_id=alice.id, total=10.0, status="pending")
        await orders.create(user_id=alice.id, total=25.0, status="complete")
        await session.commit()

        assert await users.get_by_username("alice") is not None
        assert await users.get_by_email("alice@acme.com") is not None
        assert await users.get_active_by_email("bob@abc.com") is None
        assert len(await users.active_users()) == 1
        assert len(await users.list_for_company(acme.id)) == 1

        rows, total = await users.search_page(ListQuery.from_page(page=1, size=10, order_by={"email": "asc"}))
        assert total == 1
        assert len(rows) == 1

        assert await users.pending_order_count(alice.id) == 1
        assert len(await users.for_repo(OrderRepository).orders_for_user(alice.id)) == 2

        assert await companies.get_by_slug("acme-comp") is not None
        assert await companies.get_by_name("Acme") is not None
        assert len(await companies.list_users(acme.id)) == 1
        assert await companies.count_users(acme.id) == 1

        generic_users = factory.repository(User)
        assert await generic_users.count(is_active=True) == 1

        other_users = generic_users.for_repo(UserRepository)
        assert await other_users.get_by_email("alice@acme.com") is not None

        company_from_users = other_users.for_repo(CompanyRepository)
        assert await company_from_users.get_by_slug("acme-comp") is not None

        assert await factory.companies().count_users(acme.id) == 1

    await engine.dispose()
    print(f"typed_repository_async ok (sqlphilosophy {sqlphilosophy.__version__})")


if __name__ == "__main__":
    asyncio.run(main())
