"""Module and layer rules, checked statically by imports.

* ``app.shared`` is the kernel: it imports no module and no composition root.
* ``app.modules.<m>`` reaches another module only through ``app.modules.<other>.api``;
  its domain and application code only through ``api.contracts`` (framework-free).
* Modules depend on each other without cycles.
* Inside ``shared`` and every module: ``domain`` <- ``application`` <- ``infra`` / ``presentation``.
  ``api/contracts.py`` sits at the application level, ``api/http.py`` at the presentation level.
* ``modules/<m>/module.py`` wires its module; only the composition root (``bootstrap``, the
  processes in ``entrypoints``, ``run``) imports it.
"""

import ast
import json
from collections.abc import Iterator
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import pytest

from app.entrypoints.api import app

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
    "dishka",
    "aiokafka",
    "redis",
    "aiogram",
    "aiobotocore",
    "botocore",
    "httpx",
    "croniter",
}
COMPOSITION_ROOT = ("app.bootstrap", "app.entrypoints", "app.run")
LAYERS = ("domain", "application", "infra", "presentation")
MODULES = sorted(p.name for p in (SOURCE / "modules").iterdir() if (p / "module.py").exists())


@dataclass(frozen=True)
class Location:
    """Where a Python module sits: its unit (``shared`` or a module name) and its layer."""

    unit: str | None
    layer: str | None


def locate(dotted: str) -> Location:
    parts = dotted.split(".")
    if parts[:2] == ["app", "shared"]:
        unit, rest = "shared", parts[2:]
    elif parts[:2] == ["app", "modules"] and len(parts) > 2:
        unit, rest = parts[2], parts[3:]
    else:
        return Location(None, None)
    if rest[:2] == ["api", "contracts"]:
        return Location(unit, "application")
    if rest[:2] == ["api", "http"]:
        return Location(unit, "presentation")
    if rest and rest[0] in LAYERS:
        return Location(unit, rest[0])
    return Location(unit, rest[0] if rest else None)


def dotted_name(path: Path) -> str:
    relative = path.relative_to(SOURCE.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports(path: Path) -> Iterator[str]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 or path.name == "__init__.py", f"Use absolute imports in {path}"
            if node.level == 0:
                yield node.module or ""


def sources(*parts: str) -> list[Path]:
    return sorted(p for p in SOURCE.joinpath(*parts).rglob("*.py") if "__pycache__" not in p.parts)


def edges() -> Iterator[tuple[str, Location, str, Location]]:
    """Every ``app.*`` import inside ``shared`` and ``modules``: (file, its location, target, target location)."""
    for path in [*sources("shared"), *sources("modules")]:
        name = dotted_name(path)
        for target in imports(path):
            yield name, locate(name), target, locate(target)


def violations_of(check) -> list[str]:  # type: ignore[no-untyped-def]
    return [f"{name} -> {target}" for name, here, target, there in edges() if check(name, here, target, there)]


def test_modules_are_discovered() -> None:
    assert {"auth", "users"} <= set(MODULES)


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_frameworks_or_outer_layers(layer: str) -> None:
    def bad(name: str, here: Location, target: str, there: Location) -> bool:
        if here.layer != layer:
            return False
        if target.split(".")[0] in FRAMEWORKS or target.startswith(COMPOSITION_ROOT):
            return True
        allowed = ("domain",) if layer == "domain" else ("domain", "application")
        return there.unit is not None and there.layer not in allowed

    assert not (found := violations_of(bad)), "\n".join(found)


def test_infra_does_not_import_presentation() -> None:
    def bad(name: str, here: Location, target: str, there: Location) -> bool:
        return here.layer == "infra" and there.layer == "presentation"

    assert not (found := violations_of(bad)), "\n".join(found)


def test_nothing_but_the_composition_root_imports_module_wiring() -> None:
    def bad(name: str, here: Location, target: str, there: Location) -> bool:
        if target.startswith(COMPOSITION_ROOT):
            return True
        # ``app.shared.module`` is the ``Module`` descriptor itself, not a module's wiring.
        return there.layer == "module" and there.unit != "shared"

    assert not (found := violations_of(bad)), "\n".join(found)


def test_shared_kernel_imports_no_module() -> None:
    def bad(name: str, here: Location, target: str, there: Location) -> bool:
        return here.unit == "shared" and target.startswith("app.modules")

    assert not (found := violations_of(bad)), "\n".join(found)


def test_modules_meet_only_through_their_public_api() -> None:
    def bad(name: str, here: Location, target: str, there: Location) -> bool:
        if here.unit in (None, "shared") or there.unit in (None, "shared", here.unit):
            return False
        public = f"app.modules.{there.unit}.api"
        if here.layer in ("domain", "application"):
            return not target.startswith(f"{public}.contracts")
        return not target.startswith(public)

    assert not (found := violations_of(bad)), "\n".join(found)


def test_module_dependencies_have_no_cycles() -> None:
    graph: dict[str, set[str]] = {module: set() for module in MODULES}
    for _, here, _, there in edges():
        if here.unit in graph and there.unit in graph and here.unit != there.unit:
            graph[here.unit].add(there.unit)
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        pytest.fail(f"Modules depend on each other in a cycle: {exc.args[1]}")


def test_committed_openapi_matches_the_app() -> None:
    """``docs/openapi.json`` is what the frontend sees; refresh it with ``make openapi``."""
    assert app.openapi() == json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
