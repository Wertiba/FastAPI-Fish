"""Layer rules, checked statically by imports.

``domain`` <- ``application`` <- ``infra`` / ``presentation``; ``bootstrap.py``, ``main.py`` and ``run.py``
are the composition root and may import anything.
"""

import ast
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.main import app

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "app"
FRAMEWORKS = {
    "sqlalchemy",
    "fastapi",
    "starlette",
    "pydantic",
    "prometheus_client",
    "jwt",
    "argon2",
    "uvicorn",
    "alembic",
}
COMPOSITION_ROOT = ("app.bootstrap", "app.main", "app.run")


def _imports(path: Path) -> Iterator[str]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 or path.name == "__init__.py", f"Use explicit layer imports in {path}"
            if node.level == 0:
                yield node.module or ""


def _files(layer: str) -> list[Path]:
    return sorted(p for p in (SOURCE / layer).rglob("*.py") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_frameworks_or_outer_layers(layer: str) -> None:
    violations = []
    for path in _files(layer):
        for module in _imports(path):
            relative = path.relative_to(SOURCE)
            if module.split(".")[0] in FRAMEWORKS:
                violations.append(f"{relative} -> {module}")
            if module.startswith(("app.infra", "app.presentation", *COMPOSITION_ROOT)):
                violations.append(f"{relative} -> {module}")
            if layer == "domain" and module.startswith("app.application"):
                violations.append(f"{relative} -> {module}")
            if module.startswith("dishka") and not (layer == "application" and path.name == "di.py"):
                violations.append(f"{relative} -> {module} (dishka only in application/*/di.py)")
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("layer", ["infra", "presentation"])
def test_outer_layers_do_not_import_the_composition_root(layer: str) -> None:
    violations = [
        f"{path.relative_to(SOURCE)} -> {module}"
        for path in _files(layer)
        for module in _imports(path)
        if module.startswith(COMPOSITION_ROOT)
    ]
    assert not violations, "\n".join(violations)


def test_infra_does_not_import_presentation() -> None:
    violations = [
        f"{path.relative_to(SOURCE)} -> {module}"
        for path in _files("infra")
        for module in _imports(path)
        if module.startswith("app.presentation")
    ]
    assert not violations, "\n".join(violations)


def test_committed_openapi_matches_the_app() -> None:
    """``docs/openapi.json`` is what the frontend sees; refresh it with ``make openapi``."""
    assert app.openapi() == json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
