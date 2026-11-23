"""Opt-in composite CRUD preserves all identity components and caller transactions."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from sqlphilosophy.sync.composite import CompositeRepository
from sqlphilosophy.sync.query import StatementQueryBuilder
from test_sync_repository import _FakeFactory


class CompositeBase(DeclarativeBase):
    pass


class Membership(CompositeBase):
    __tablename__ = "composite_membership"
    tenant_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class Scalar(CompositeBase):
    __tablename__ = "composite_scalar"
    id: Mapped[int] = mapped_column(primary_key=True)


@pytest.fixture
def composite_session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    CompositeBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def repository(session: Session) -> CompositeRepository[Membership]:
    return CompositeRepository(Membership, session, _FakeFactory(session))


def test_composite_crud_distinguishes_complete_keys_and_leaves_commit_to_caller(composite_session: Session) -> None:
    repo = repository(composite_session)
    assert repo.session is composite_session
    assert repo.model is Membership
    assert repo.factory.session is composite_session
    first = repo.add(Membership(tenant_id=1, user_id=1, title="First"))
    repo.add(Membership(tenant_id=1, user_id=2, title="Second"))
    repo.add(Membership(tenant_id=2, user_id=1, title="Other tenant"))
    assert repo.find_entity(criteria=repo.criteria((1, 1))) is first
    assert repo.find_entity(criteria=repo.criteria((1, 99))) is None
    assert repo.update_partial((1, 1), {"title": "Changed"}, frozenset({"title"})) == 1
    assert first.title == "Changed"
    assert repo.find_entity(criteria=repo.criteria((2, 1))).title == "Other tenant"
    assert repo.update_partial((1, 99), {"title": "Missing"}, frozenset({"title"})) == 0
    assert repo.update_partial((1, 1), {}, frozenset({"title"})) == 0
    assert repo.remove((1, 2)) is True
    assert repo.remove((1, 2)) is False
    assert repo.find_entity(criteria=repo.criteria((2, 1))) is not None
    composite_session.rollback()
    assert composite_session.scalars(select(Membership)).all() == []


def test_composite_lookup_preserves_repository_scope_and_lock(composite_session: Session) -> None:
    class TenantRepository(CompositeRepository[Membership]):
        def apply_scope(self, statement: StatementQueryBuilder[Membership]) -> StatementQueryBuilder[Membership]:
            return statement.where(Membership.tenant_id == 1)

    repo = TenantRepository(Membership, composite_session, _FakeFactory(composite_session))
    repo.add(Membership(tenant_id=1, user_id=1, title="Visible"))
    repo.add(Membership(tenant_id=2, user_id=1, title="Hidden"))
    with patch("sqlphilosophy.sync.query.SqlAlchemyStatementBuilder.with_for_update", autospec=True) as locked:
        locked.side_effect = lambda statement: statement
        assert repo.find_entity(criteria=repo.criteria((1, 1)), lock=True).title == "Visible"
        locked.assert_called_once()
    assert repo.find_entity(criteria=repo.criteria((2, 1))) is None
    with pytest.raises(ValueError, match="explicit criteria"):
        repo.find_entity(criteria=())


@pytest.mark.parametrize("identity", [(), (1,), (1, 2, 3), [1, 2], "1,2", (True, 2), (1, "2"), (1.0, 2), (None, 2)])
def test_composite_criteria_rejects_missing_and_wrong_scalar_components(composite_session: Session, identity) -> None:
    repo = repository(composite_session)
    with pytest.raises(ValueError, match="identity"):
        repo.criteria(identity)


def test_composite_requires_multiple_primary_columns(composite_session: Session) -> None:
    with pytest.raises(ValueError, match="multiple primary-key"):
        CompositeRepository(Scalar, composite_session, _FakeFactory(composite_session))


@pytest.mark.parametrize(
    ("fields", "writable"),
    [
        ({"title": "Changed"}, frozenset()),
        ({"title": "Changed"}, frozenset({"not_a_column"})),
        ({"tenant_id": 2}, frozenset({"tenant_id"})),
        ({"user_id": 2}, frozenset({"user_id"})),
        ({"active": False}, frozenset({"title"})),
        ({"unknown": True}, frozenset({"title"})),
    ],
)
def test_composite_updates_enforce_mapped_nonidentity_allowlist(composite_session: Session, fields, writable) -> None:
    repo = repository(composite_session)
    row = repo.add(Membership(tenant_id=1, user_id=1, title="Original"))
    with pytest.raises(ValueError, match="allowlist"):
        repo.update_partial((1, 1), fields, writable)
    composite_session.refresh(row)
    assert row.title == "Original"
    assert row.tenant_id == 1
    assert row.user_id == 1
    assert row.active


def test_composite_duplicate_failure_remains_caller_rollback(composite_session: Session) -> None:
    repo = repository(composite_session)
    repo.add(Membership(tenant_id=1, user_id=1, title="First"))
    duplicate = Membership(tenant_id=1, user_id=1, title="Duplicate")
    with pytest.raises(IntegrityError):
        repo.add(duplicate)
    composite_session.rollback()
    assert composite_session.scalars(select(Membership)).all() == []
