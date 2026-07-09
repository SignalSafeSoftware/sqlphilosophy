"""Import contract: canonical paths work; forbidden paths fail."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_canonical_imports() -> None:
    from sqlphilosophy.aio.protocols import AsyncBaseRepositoryProtocol, AsyncRepositoryFactory
    from sqlphilosophy.aio.query import AsyncSqlAlchemyStatementBuilder
    from sqlphilosophy.aio.repository import AsyncBaseRepository
    from sqlphilosophy.audit.context import audit_context
    from sqlphilosophy.audit.model import TimestampModel
    from sqlphilosophy.sorting import ListQuery
    from sqlphilosophy.sync.protocols import BaseRepositoryProtocol, RepositoryFactory
    from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder
    from sqlphilosophy.sync.repository import BaseRepository

    _ = (
        BaseRepository,
        BaseRepositoryProtocol,
        SqlAlchemyStatementBuilder,
        RepositoryFactory,
        AsyncBaseRepository,
        AsyncBaseRepositoryProtocol,
        AsyncSqlAlchemyStatementBuilder,
        AsyncRepositoryFactory,
        ListQuery,
        audit_context,
        TimestampModel,
    )


def test_trusted_sql_canonical_imports() -> None:
    from sqlphilosophy.trusted_sql import (
        col_eq,
        col_icontains,
        col_range,
        literal_order_expr,
        order_by_allowlist,
        order_expr_from_sort,
        sql_table,
    )

    _ = (
        sql_table,
        col_eq,
        col_icontains,
        col_range,
        literal_order_expr,
        order_by_allowlist,
        order_expr_from_sort,
    )


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


def test_root_package_exposes_version_only() -> None:
    import sqlphilosophy

    assert sqlphilosophy.__all__ == ["__version__"]
    assert isinstance(sqlphilosophy.__version__, str)
    assert sqlphilosophy.__version__
    for attr in ("BaseRepository", "AsyncBaseRepository", "SortConfig"):
        assert not hasattr(sqlphilosophy, attr)


def test_load_version_prefers_installed_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from importlib import metadata

    import sqlphilosophy

    monkeypatch.setattr(metadata, "version", lambda _name: "1.2.3")
    assert sqlphilosophy._load_version() == "1.2.3"


def test_load_version_reads_bundled_file_when_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from importlib import metadata

    import sqlphilosophy

    def _missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", _missing)
    version_file = Path(sqlphilosophy.__file__).resolve().parent / "VERSION"
    assert sqlphilosophy._load_version() == version_file.read_text(encoding="utf-8").strip()


def test_audit_package_has_no_reexports() -> None:
    import sqlphilosophy.audit as audit_pkg

    assert audit_pkg.__all__ == []
    with pytest.raises(ImportError):
        from sqlphilosophy.audit import TimestampModel  # noqa: F401
