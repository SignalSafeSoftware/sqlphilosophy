"""Strongly typed domain repositories with a session-scoped factory.

Run from the repo root::

    uv run python examples/typed_repository_sync.py
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import cast

from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from sqlphilosophy.sync.protocols import RepositoryFactory
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
from sqlphilosophy.sync.query import StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository

T = TypeVar("T", bound=DeclarativeBase)
U = TypeVar("U", bound='BaseRepository[T, "AppRepositoryFactory"]')  # type: ignore[valid-type]


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


class UserRepository(BaseRepository[User, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``User``."""

    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(User, session, factory)
        self._app_factory = factory

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def get_by_username(self, username: str) -> User | None:
        return self.first(username=username)

    def list_for_company(self, company_id: int) -> list[User]:
        return list(self.filter(company_id=company_id))

    def get_active_by_email(self, email: str) -> User | None:
        return (
            self.statement()
            .where(User.email == email, User.is_active.is_(True))
            .scalars()
            .first()
        )


class CompanyRepository(BaseRepository[Company, "AppRepositoryFactory"]):
    """Domain repository with typed query helpers for ``Company``."""

    def __init__(self, session: Session, factory: AppRepositoryFactory) -> None:
        super().__init__(Company, session, factory)
        self._app_factory = factory

    def get_by_slug(self, slug: str) -> Company | None:
        return self.first(slug=slug)

    def get_by_name(self, name: str) -> Company | None:
        return self.first(name=name)

    def list_users(self, company_id: int) -> list[User]:
        return self._app_factory.users().list_for_company(company_id)

    def count_users(self, company_id: int) -> int:
        return self._app_factory.users().count(company_id=company_id)


class AppRepositoryFactory(RepositoryFactory, Protocol):
    """App-specific factory surface: typed repos plus sqlphilosophy factory methods."""

    def companies(self) -> CompanyRepository: ...

    def users(self) -> UserRepository: ...


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
        return BaseRepository(
            model,
            self._session,
            cast(AppRepositoryFactory, self),
        )

    def companies(self) -> CompanyRepository:
        return self.get_repository(CompanyRepository)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)


def main() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as session:
        factory = SessionRepositoryFactory(session)

        companies = factory.companies()
        acme = companies.add(Company(name="Acme", slug="acme-comp"))
        abc = companies.add(Company(name="ABC", slug="abc-comp"))
        session.flush()

        users = factory.users()
        users.add(
            User(
                username="alice",
                email="alice@acme.com",
                is_active=True,
                company_id=acme.id,
            )
        )
        users.add(
            User(
                username="bob",
                email="bob@abc.com",
                is_active=False,
                company_id=abc.id,
            )
        )
        session.commit()

        assert users.get_by_username("alice") is not None
        assert users.get_by_email("alice@acme.com") is not None
        assert users.get_active_by_email("bob@abc.com") is None
        assert len(users.list_for_company(acme.id)) == 1
        assert len(users.list_for_company(abc.id)) == 1

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


if __name__ == "__main__":
    main()
