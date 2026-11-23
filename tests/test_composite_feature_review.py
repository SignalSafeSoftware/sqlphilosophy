"""Composite writable guards use mapped attribute names, including renamed columns."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from sqlphilosophy.sync.composite import CompositeRepository
from test_sync_repository import _FakeFactory


class Base(DeclarativeBase):
    pass


class RenamedIdentity(Base):
    __tablename__ = "review_composite_renamed"
    tenant_id: Mapped[int] = mapped_column("tenant_key", primary_key=True)
    item_id: Mapped[int] = mapped_column("item_key", primary_key=True)
    name: Mapped[str]


def test_composite_repository_rejects_renamed_primary_key_writes_before_sql() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        repository = CompositeRepository(RenamedIdentity, session, None)
        repository.add(RenamedIdentity(tenant_id=1, item_id=1, name="Original"))
        for identity_field in ("tenant_id", "item_id"):
            writable = frozenset({identity_field, "name"})
            with pytest.raises(ValueError, match="non-identity writable"):
                repository.update_partial((1, 1), {identity_field: 2}, writable)
        assert repository.update_partial((1, 1), {"name": "Changed"}, frozenset({"name"})) == 1
        row = repository.find_entity(criteria=repository.criteria((1, 1)))
        assert row is not None
        assert (row.tenant_id, row.item_id, row.name) == (1, 1, "Changed")
    engine.dispose()


def test_composite_statement_preserves_host_factory_customization() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():

        class ScopedFactory(_FakeFactory):
            def create_statement(self, model):
                return super().create_statement(model).where(model.name != "Hidden")

        factory = ScopedFactory(session)
        repository = CompositeRepository(RenamedIdentity, session, factory)
        repository.add(RenamedIdentity(tenant_id=1, item_id=1, name="Visible"))
        repository.add(RenamedIdentity(tenant_id=1, item_id=2, name="Hidden"))
        assert repository.find_entity(criteria=repository.criteria((1, 1))) is not None
        assert repository.find_entity(criteria=repository.criteria((1, 2))) is None
        assert factory.created == [RenamedIdentity, RenamedIdentity]
    engine.dispose()


def test_composite_statement_without_factory_retains_portable_fallback() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        repository = CompositeRepository(RenamedIdentity, session)
        assert repository.maybe_factory is None
        row = repository.add(RenamedIdentity(tenant_id=1, item_id=1, name="Standalone"))
        assert repository.find_entity(criteria=repository.criteria((1, 1))) is row
    engine.dispose()
