"""Генератор нового домена с рабочим CRUD — во все слои сразу.

    uv run python scripts/new_domain.py projects             # сущность Project (угадывается)
    uv run python scripts/new_domain.py task_lists TaskList  # сущность указана явно
    make domain name=projects                                # то же через make

Создаёт файлы домена в каждом слое (domain / application / infra / presentation), e2e-тест
``tests/api/test_<domain>_endpoints.py`` и регистрирует домен в общих точках сборки: модель в
``infra/database/__init__.py`` (для Alembic), gateway-провайдер, провайдер интеракторов, роутер, маппинг ошибок.
Поля сущности описаны в модели (она же таблица), во входных схемах application и в схеме ответа.
Дальше — миграция и ваша предметная логика.
"""

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).resolve().parent / "domain_template"
APP = ROOT / "src" / "app"

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ENTITY_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
RESERVED = {"users", "auth", "refresh_tokens", "health", "metrics", "metadata", "base", "schema", "ports", "errors"}


def camel(snake_name: str) -> str:
    return "".join(part.capitalize() for part in snake_name.split("_"))


def snake(camel_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_name).lower()


def singular(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("ses", "xes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def render(text: str, ctx: dict[str, str]) -> str:
    for key, value in ctx.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def insert_after_last(source: str, pattern: str, text: str, path: Path) -> str:
    matches = list(re.finditer(pattern, source, flags=re.M))
    if not matches:
        sys.exit(f"{path.relative_to(ROOT)}: не найдено место для вставки ({pattern})")
    end = matches[-1].end()
    return source[:end] + text + source[end:]


def insert_before(source: str, anchor: str, text: str, path: Path, *, last: bool = False) -> str:
    index = source.rfind(anchor) if last else source.find(anchor)
    if index < 0:
        sys.exit(f"{path.relative_to(ROOT)}: не найдено место для вставки ({anchor!r})")
    return source[:index] + text + source[index:]


def patch(path: Path, edit: Callable[[str, Path], str]) -> None:
    path.write_text(edit(path.read_text(encoding="utf-8"), path), encoding="utf-8")


def register(ctx: dict[str, str]) -> list[Path]:
    """Вписывает домен в общие точки сборки. Импорты потом упорядочит ruff."""
    plural, entity, entity_cls = ctx["plural"], ctx["entity"], ctx["Entity"]
    imp_domain = f"from app.domain.{plural}.entity import {entity_cls}\n"
    paths = {
        "metadata": APP / "infra" / "database" / "__init__.py",
        "gateways": APP / "infra" / "gateways" / "di.py",
        "bootstrap": APP / "bootstrap.py",
        "routers": APP / "presentation" / "http" / "api" / "v1" / "endpoints" / "__init__.py",
        "exc_map": APP / "presentation" / "http" / "api" / "v1" / "exceptions" / "exc_map.py",
    }

    def metadata(src: str, path: Path) -> str:
        src = insert_after_last(src, r"^from app\.domain\..+\n", imp_domain, path)
        return re.sub(r"^__all__ = \[", f'__all__ = ["{entity_cls}", ', src, count=1, flags=re.M)

    def gateways(src: str, path: Path) -> str:
        src = insert_after_last(
            src,
            r"^from app\..+\n",
            f"from app.application.ports.{entity}_gateway import {entity_cls}Gateway\n"
            f"from app.infra.gateways.{entity} import SqlAlchemy{entity_cls}Gateway\n",
            path,
        )
        return src + f"    {entity} = provide(SqlAlchemy{entity_cls}Gateway, provides={entity_cls}Gateway)\n"

    def bootstrap(src: str, path: Path) -> str:
        provider_import = f"from app.application.{plural}.di import {entity_cls}Provider\n"
        src = insert_after_last(src, r"^from app\.application\..+\n", provider_import, path)
        return insert_before(src, "        *providers,", f"        {entity_cls}Provider(),\n", path)

    def routers(src: str, path: Path) -> str:
        router_import = f"from .{plural} import router as {entity}_router\n"
        src = insert_after_last(src, r"^from \.\w+ import router as \w+\n", router_import, path)
        return src + f"router.include_router({entity}_router)\n"

    def exc_map(src: str, path: Path) -> str:
        error_import = f"from app.domain.{plural}.errors import {entity_cls}NotFoundError\n"
        src = insert_after_last(src, r"^from app\.domain\.errors import .+\n", error_import, path)
        entry = (
            f"    {entity_cls}NotFoundError: lambda path, exc: NotFound(\n"
            f"        path=path,\n"
            f'        message="{ctx["Title"]} not found",\n'
            f"    ),\n"
        )
        return insert_before(src, "}\n", entry, path, last=True)

    for name, edit in (
        ("metadata", metadata),
        ("gateways", gateways),
        ("bootstrap", bootstrap),
        ("routers", routers),
        ("exc_map", exc_map),
    ):
        patch(paths[name], edit)
    return list(paths.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plural", help="имя домена во мн. числе, snake_case: projects, task_lists")
    parser.add_argument("entity", nargs="?", help="имя сущности, CamelCase: Project, TaskList")
    args = parser.parse_args()

    plural: str = args.plural
    if not NAME_RE.match(plural) or plural in RESERVED:
        sys.exit(f"Некорректное или зарезервированное имя домена: {plural!r}")
    entity_cls: str = args.entity or camel(singular(plural))
    if not ENTITY_RE.match(entity_cls):
        sys.exit(f"Некорректное имя сущности: {entity_cls!r}")
    entity = snake(entity_cls)
    if entity == plural:
        sys.exit("Имя домена (мн. ч.) должно отличаться от имени сущности: укажите сущность явно")

    ctx = {
        "plural": plural,
        "Plural": camel(plural),
        "entity": entity,
        "Entity": entity_cls,
        "url": plural.replace("_", "-"),
        "Tag": camel(plural),
        "Title": entity.replace("_", " ").capitalize(),
    }

    targets = {
        "domain_entity.py.tmpl": APP / "domain" / plural / "entity.py",
        "domain_errors.py.tmpl": APP / "domain" / plural / "errors.py",
        "port.py.tmpl": APP / "application" / "ports" / f"{entity}_gateway.py",
        "app_schemas.py.tmpl": APP / "application" / plural / "schemas.py",
        "app_interactors.py.tmpl": APP / "application" / plural / "interactors.py",
        "app_di.py.tmpl": APP / "application" / plural / "di.py",
        "gateway.py.tmpl": APP / "infra" / "gateways" / f"{entity}.py",
        "schemas.py.tmpl": APP / "presentation" / "http" / "schemas" / f"{entity}.py",
        "endpoints.py.tmpl": APP / "presentation" / "http" / "api" / "v1" / "endpoints" / f"{plural}.py",
        "test_endpoints.py.tmpl": ROOT / "tests" / "api" / f"test_{plural}_endpoints.py",
    }
    existing = [path for path in (APP / "domain" / plural, *targets.values()) if path.exists()]
    if existing:
        sys.exit("Уже существует: " + ", ".join(str(path.relative_to(ROOT)) for path in existing))

    for template, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render((TEMPLATE / template).read_text(encoding="utf-8"), ctx), encoding="utf-8")
    for package in (APP / "domain" / plural, APP / "application" / plural):
        (package / "__init__.py").touch()

    changed = [*targets.values(), *register(ctx)]
    files = [str(path) for path in changed]
    # Упорядочить вставленные импорты и привести стиль; без ruff код всё равно рабочий.
    subprocess.run(["uv", "run", "ruff", "check", "--fix", "--quiet", *files], cwd=ROOT, check=False)
    subprocess.run(["uv", "run", "ruff", "format", "--quiet", *files], cwd=ROOT, check=False)
    # docs/openapi.json сверяется с приложением в tests/architecture.
    subprocess.run(["uv", "run", "python", "scripts/export_openapi.py"], cwd=ROOT, check=False)

    print(f"Домен {plural} (сущность {entity_cls}) создан: /api/v1/{ctx['url']}. Дальше:")
    print(f'  make migration m="add {plural}" && make migrate')
    print(f"  uv run pytest tests/api/test_{plural}_endpoints.py")


if __name__ == "__main__":
    main()
