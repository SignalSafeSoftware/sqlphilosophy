"""Async strongly typed domain repositories with a session-scoped factory.

Run from the repo root::

    uv run python examples/typed_repository_async.py
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import cast

from sqlalchemy import ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
from sqlphilosophy.aio.query import AsyncStatementQueryBuilder
from sqlphilosophy.aio.repository import AsyncBaseRepository

T = TypeVar("T", bound=DeclarativeBase)
U = TypeVar("U", bound='AsyncBaseRepository[T, "AppRepositoryFactory"]')  # type: ignore[valid-type]


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    users: Mapped[list["User"]] = relationship(back_populates="company")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    company: Mapped[Company] = relationship(back_populates="users")


class UserRepository(AsyncBaseRepository[User, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``User``."""

    def __init__(self, session: AsyncSession, factory: AppRepositoryFactory) -> None:
        super().__init__(User, session, factory)
        self._app_factory = factory

    async def get_by_email(self, email: str) -> User | None:
        return await self.first(email=email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.first(username=username)

    async def list_for_company(self, company_id: int) -> list[User]:
        return list(await self.filter(company_id=company_id))

    async def get_active_by_email(self, email: str) -> User | None:
        return (
            await self.statement()
            .where(User.email == email, User.is_active.is_(True))
            .scalars()
            .first()
        )


class CompanyRepository(AsyncBaseRepository[Company, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``Company``."""

    def __init__(self, session: AsyncSession, factory: AppRepositoryFactory) -> None:
        super().__init__(Company, session, factory)
        self._app_factory = factory

    async def get_by_slug(self, slug: str) -> Company | None:
        return await self.first(slug=slug)

    async def get_by_name(self, name: str) -> Company | None:
        return await self.first(name=name)

    async def list_users(self, company_id: int) -> list[User]:
        return await self._app_factory.users().list_for_company(company_id)

    async def count_users(self, company_id: int) -> int:
        return await self._app_factory.users().count(company_id=company_id)


class AppRepositoryFactory(AsyncRepositoryFactory, Protocol):
    """App-specific factory surface: typed repos plus sqlphilosophy factory methods."""

    def companies(self) -> CompanyRepository: ...

    def users(self) -> UserRepository: ...


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
        return AsyncBaseRepository(
            model,
            self._session,
            cast(AppRepositoryFactory, self),
        )

    def companies(self) -> CompanyRepository:
        return self.get_repository(CompanyRepository)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        factory = AsyncSessionRepositoryFactory(session)

        companies = factory.companies()
        acme = await companies.add(Company(name="Acme", slug="acme-comp"))
        abc = await companies.add(Company(name="ABC", slug="abc-comp"))
        await session.flush()

        users = factory.users()
        await users.add(
            User(
                username="alice",
                email="alice@acme.com",
                is_active=True,
                company_id=acme.id,
            )
        )
        await users.add(
            User(
                username="bob",
                email="bob@abc.com",
                is_active=False,
                company_id=abc.id,
            )
        )
        await session.commit()

        assert await users.get_by_username("alice") is not None
        assert await users.get_by_email("alice@acme.com") is not None
        assert await users.get_active_by_email("bob@abc.com") is None
        assert len(await users.list_for_company(acme.id)) == 1
        assert len(await users.list_for_company(abc.id)) == 1

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


if __name__ == "__main__":
    asyncio.run(main())
