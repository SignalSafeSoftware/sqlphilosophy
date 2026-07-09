"""SQLAlchemy repository kit — sync/async CRUD, query builders, sort, and SQL helpers."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

__all__ = ["__version__"]


def _load_version() -> str:
    try:
        return metadata.version("sqlphilosophy")
    except metadata.PackageNotFoundError:
        return (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()


__version__ = _load_version()
