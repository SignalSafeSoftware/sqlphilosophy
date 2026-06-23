"""Import contract: canonical paths work; forbidden paths fail."""

from __future__ import annotations
import importlib
import pytest


def test_canonical_imports() -> None:
    from sqlphilosophy.aio.protocols import AsyncRepositoryFactory
    from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
    from sqlphilosophy.aio.repository import AsyncBaseRepository
    from sqlphilosophy.audit.context import audit_context
    from sqlphilosophy.audit.model import TimestampModel
    from sqlphilosophy.sorting import ListQuery
    from sqlphilosophy.sync.protocols import RepositoryFactory
    from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
    from sqlphilosophy.sync.repository import BaseRepository

    assert BaseRepository is not None
    assert SqlAlchemyStatementBuilder is not None
    assert RepositoryFactory is not None
    assert AsyncBaseRepository is not None
    assert AsyncSqlAlchemyStatementBuilder is not None
    assert AsyncRepositoryFactory is not None
    assert ListQuery is not None
    assert audit_context is not None
    assert TimestampModel is not None


@pytest.mark.parametrize(
    "module_name",
    [
        "sqlphilosophy.base",
        "sqlphilosophy.factory",
        "sqlphilosophy.sort",
        "sqlphilosophy.protocols",
        "sqlphilosophy.async_base",
        "sqlphilosophy.async_factory",
    ],
)
def test_forbidden_compatibility_modules_missing(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_root_package_has_no_reexports() -> None:
    import sqlphilosophy

    assert sqlphilosophy.__all__ == []
    for attr in ("BaseRepository", "AsyncBaseRepository", "SortConfig"):
        assert not hasattr(sqlphilosophy, attr)


def test_audit_package_has_no_reexports() -> None:
    import sqlphilosophy.audit as audit_pkg

    assert audit_pkg.__all__ == []
    with pytest.raises(ImportError):
        from sqlphilosophy.audit import TimestampModel  # noqa: F401
