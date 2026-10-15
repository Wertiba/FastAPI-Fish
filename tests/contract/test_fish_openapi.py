"""Контракт API = FastAPI-Fish.

``fish_openapi.json`` снят с кода FastAPI-Fish. Всё, что есть в нём (пути, методы,
параметры, тела, ответы, operationId, компоненты схем), должно один в один совпадать
с нашим OpenAPI. Новые домены добавляют свои пути и схемы — это не нарушение.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.bootstrap.config import Settings
from app.main import create_app

FISH = json.loads((Path(__file__).parent / "fish_openapi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ours() -> dict[str, Any]:
    settings = Settings(_env_file=None, APP_SECURITY_JWT_SECRET="contract", LOG_FILE="", LOG_LEVEL="WARNING")
    return create_app(settings).openapi()


FISH_OPERATIONS = [(path, method) for path, item in FISH["paths"].items() for method in item]


@pytest.mark.parametrize(
    ("path", "method"), FISH_OPERATIONS, ids=[f"{m.upper()} {p}" for p, m in FISH_OPERATIONS]
)
def test_operation_matches_fish(ours: dict[str, Any], path: str, method: str) -> None:
    assert path in ours["paths"], f"нет пути {path}"
    assert ours["paths"][path].get(method) == FISH["paths"][path][method]


@pytest.mark.parametrize("name", sorted(FISH["components"]["schemas"]))
def test_schema_component_matches_fish(ours: dict[str, Any], name: str) -> None:
    assert ours["components"]["schemas"].get(name) == FISH["components"]["schemas"][name]


def test_paths_order_and_metadata_match_fish(ours: dict[str, Any]) -> None:
    fish_paths = list(FISH["paths"])
    our_paths = [p for p in ours["paths"] if p in FISH["paths"]]
    assert our_paths == fish_paths
    assert ours["info"] == FISH["info"]
    assert ours["openapi"] == FISH["openapi"]
