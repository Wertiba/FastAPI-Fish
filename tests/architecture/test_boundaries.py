"""Архитектурные правила, проверяемые статически (по import'ам).

1. Модуль импортирует из другого модуля только его ``public.py``.
2. ``domain`` — чистый Python: только stdlib и ``shared.domain``.
3. ``application`` не знает про FastAPI/SQLAlchemy и про infrastructure/presentation.
4. ``shared`` не импортирует модули.

Composition root (``app/main.py``, ``app/bootstrap``, ``app/modules/registry.py``)
вправе импортировать что угодно — там всё и собирается.
"""

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
APP = SRC / "app"
MODULES_DIR = APP / "modules"
FRAMEWORKS = ("fastapi", "starlette", "sqlalchemy", "dishka", "alembic", "jwt", "argon2")


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC).with_suffix("").parts)


def _imports(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


MODULE_NAMES = sorted(p.name for p in MODULES_DIR.iterdir() if (p / "module.py").exists())


def test_modules_are_discovered() -> None:
    assert {"users", "auth"} <= set(MODULE_NAMES)


@pytest.mark.parametrize("module", MODULE_NAMES)
def test_cross_module_imports_go_through_public(module: str) -> None:
    violations = []
    for path in _python_files(MODULES_DIR / module):
        for imported in _imports(path):
            for other in MODULE_NAMES:
                prefix = f"app.modules.{other}"
                if other != module and imported.startswith(prefix) and imported != f"{prefix}.public":
                    violations.append(f"{_module_name(path)} -> {imported}")
    assert not violations, "Импортируйте другие модули только через их public.py:\n" + "\n".join(violations)


@pytest.mark.parametrize("module", MODULE_NAMES)
def test_domain_is_pure(module: str) -> None:
    """domain импортирует только stdlib, shared.domain и свой же domain."""
    allowed = ("app.shared.domain", f"app.modules.{module}.domain")
    violations = [
        f"{_module_name(path)} -> {imported}"
        for path in _python_files(MODULES_DIR / module / "domain")
        for imported in _imports(path)
        if (imported.startswith("app.") and not imported.startswith(allowed))
        or (not imported.startswith("app.") and imported.split(".")[0] not in sys.stdlib_module_names)
    ]
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("module", MODULE_NAMES)
def test_application_does_not_depend_on_outer_layers(module: str) -> None:
    application = MODULES_DIR / module / "application"
    violations = [
        f"{_module_name(path)} -> {imported}"
        for path in _python_files(application)
        for imported in _imports(path)
        if imported.startswith(FRAMEWORKS) or ".infrastructure" in imported or ".presentation" in imported
    ]
    assert not violations, "\n".join(violations)


def test_shared_kernel_does_not_import_modules() -> None:
    violations = [
        f"{_module_name(path)} -> {imported}"
        for path in _python_files(APP / "shared")
        for imported in _imports(path)
        if imported.startswith("app.modules") or imported.startswith("app.bootstrap")
    ]
    assert not violations, "\n".join(violations)
