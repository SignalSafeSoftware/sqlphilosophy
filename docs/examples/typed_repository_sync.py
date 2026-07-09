"""Strongly typed domain repositories with a session-scoped factory.

Run from the repo root::

    uv run --extra dev python docs/examples/typed_repository_sync.py
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, cast

from sqlalchemy import ForeignKey, Numeric, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

import sqlphilosophy
from sqlphilosophy.sorting import ListQuery, SortConfig, SortSpec
from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository
from sqlphilosophy.types import PrimaryKey, RowMapping

T = TypeVar("T", bound=DeclarativeBase)
U = TypeVar("U", bound='BaseRepository[T, "AppRepositoryFactory"]')  # type: ignore[valid-type]


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


class UserRepository(BaseRepository[User, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``User``."""

    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def _app_factory(self) -> AppRepositoryFactory:
        if self._factory is None:
            raise RuntimeError("AppRepositoryFactory is required")
        return cast(AppRepositoryFactory, self._factory)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def get_by_username(self, username: str) -> User | None:
        return self.first(username=username)

    def active_users(self) -> list[User]:
        return list(self.filter(is_active=True))

    def list_for_company(self, company_id: int) -> list[User]:
        return list(self.filter(company_id=company_id))

    def get_active_by_email(self, email: str) -> User | None:
        return self.statement().where(User.email == email, User.is_active.is_(True)).scalars().first()

    def search_page(self, query: ListQuery) -> tuple[list[RowMapping], int]:
        sort = SortConfig(
            default=SortSpec("email", "asc"),
            columns={
                "email": {"asc": User.email, "desc": User.email.desc()},
                "username": {"asc": User.username, "desc": User.username.desc()},
            },
        )
        return self.statement().where(User.is_active.is_(True)).fetch_page(query, sort=sort)

    def pending_order_count(self, user_id: PrimaryKey) -> int:
        return self.for_repo(OrderRepository).count_for_user(user_id, status="pending")


class OrderRepository(BaseRepository[Order, "AppRepositoryFactory"]):
    """Domain repository for ``Order`` rows."""

    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(Order, session, factory)

    def count_for_user(self, user_id: PrimaryKey, *, status: str | None = None) -> int:
        filters: dict[str, object] = {"user_id": user_id}
        if status is not None:
            filters["status"] = status
        return self.count(**filters)

    def orders_for_user(self, user_id: PrimaryKey) -> list[Order]:
        return list(self.filter(user_id=user_id))


class CompanyRepository(BaseRepository[Company, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``Company``."""

    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(Company, session, factory)

    def _app_factory(self) -> AppRepositoryFactory:
        if self._factory is None:
            raise RuntimeError("AppRepositoryFactory is required")
        return cast(AppRepositoryFactory, self._factory)

    def get_by_slug(self, slug: str) -> Company | None:
        return self.first(slug=slug)

    def get_by_name(self, name: str) -> Company | None:
        return self.first(name=name)

    def list_users(self, company_id: int) -> list[User]:
        return self._app_factory().users().list_for_company(company_id)

    def count_users(self, company_id: int) -> int:
        return self._app_factory().users().count(company_id=company_id)


class AppRepositoryFactory(RepositoryFactory, Protocol):
    """App-specific factory surface: typed repos plus sqlphilosophy factory methods."""

    def companies(self) -> CompanyRepository: ...

    def users(self) -> UserRepository: ...

    def orders(self) -> OrderRepository: ...


class SessionRepositoryFactory:
    """Session-scoped factory implementing ``AppRepositoryFactory``."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repositories: dict[Any, Any] = {}

    def create_statement(self, model: type[T]) -> StatementQueryBuilder[T]:
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type[U]) -> U:
        cached = self._repositories.get(repo_class)
        if cached is None:
            constructor = cast(
                Callable[[Session, AppRepositoryFactory], U],
                repo_class,
            )
            cached = constructor(self._session, cast(AppRepositoryFactory, self))
            self._repositories[repo_class] = cached
        return cast(U, cached)

    def repository(self, model: type[T]) -> BaseRepository[T, AppRepositoryFactory]:
        return BaseRepository(model, self._session, cast(AppRepositoryFactory, self))

    def companies(self) -> CompanyRepository:
        return self.get_repository(CompanyRepository)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)

    def orders(self) -> OrderRepository:
        return self.get_repository(OrderRepository)


def main() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        factory = SessionRepositoryFactory(session)

        companies = factory.companies()
        acme = companies.create(name="Acme", slug="acme-comp")
        abc = companies.create(name="ABC", slug="abc-comp")
        session.flush()

        users = factory.users()
        alice = users.create(
            username="alice",
            email="alice@acme.com",
            is_active=True,
            company_id=acme.id,
        )
        users.create(
            username="bob",
            email="bob@abc.com",
            is_active=False,
            company_id=abc.id,
        )
        session.flush()

        orders = factory.orders()
        orders.create(user_id=alice.id, total=10.0, status="pending")
        orders.create(user_id=alice.id, total=25.0, status="complete")
        session.commit()

        assert users.get_by_username("alice") is not None
        assert users.get_by_email("alice@acme.com") is not None
        assert users.get_active_by_email("bob@abc.com") is None
        assert len(users.active_users()) == 1
        assert len(users.list_for_company(acme.id)) == 1

        rows, total = users.search_page(ListQuery.from_page(page=1, size=10, order_by={"email": "asc"}))
        assert total == 1
        assert len(rows) == 1

        assert users.pending_order_count(alice.id) == 1
        assert len(users.for_repo(OrderRepository).orders_for_user(alice.id)) == 2

        assert companies.get_by_slug("acme-comp") is not None
        assert companies.get_by_name("Acme") is not None
        assert len(companies.list_users(acme.id)) == 1
        assert companies.count_users(acme.id) == 1

        generic_users = factory.repository(User)
        assert generic_users.count(is_active=True) == 1

        other_users = generic_users.for_repo(UserRepository)
        assert other_users.get_by_email("alice@acme.com") is not None

        company_from_users = other_users.for_repo(CompanyRepository)
        assert company_from_users.get_by_slug("acme-comp") is not None

        assert factory.companies().count_users(acme.id) == 1

    print(f"typed_repository_sync ok (sqlphilosophy {sqlphilosophy.__version__})")


if __name__ == "__main__":
    main()
