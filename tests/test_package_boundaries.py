"""Guardrails: sqlphilosophy must stay free of app/framework imports."""

from __future__ import annotations
import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1] / "src" / "sqlphilosophy"

_ORM_FRAMEWORK_ROOT = "dj" + "ango"

_FORBIDDEN_ROOTS = frozenset(
    {
        _ORM_FRAMEWORK_ROOT,
        "rest_framework",
        "celery",
        "vega",
        "phobos",
        "backend",
    }
)


def _violations_in_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _FORBIDDEN_ROOTS:
                    bad.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in _FORBIDDEN_ROOTS:
                bad.append(node.module)
    return bad


def test_sqlphilosophy_has_no_framework_or_app_imports() -> None:
    assert _PKG.is_dir(), f"missing package: {_PKG}"
    for path in sorted(_PKG.rglob("*.py")):
        violations = _violations_in_file(path)
        assert not violations, f"{path}: forbidden imports {violations}"
