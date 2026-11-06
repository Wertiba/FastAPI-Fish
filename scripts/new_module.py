"""Генератор нового модуля с рабочим CRUD.

    uv run python scripts/new_module.py projects             # сущность Project (угадывается)
    uv run python scripts/new_module.py task_lists TaskList  # сущность указана явно
    make module name=projects                                # то же через make

Создаёт ``src/app/modules/<имя>/`` со всеми слоями (domain / application / infra / presentation),
публичным ``api/`` и ``module.py``, e2e-тест ``tests/api/test_<имя>_endpoints.py`` и добавляет
модуль в ``MODULES`` в ``app/bootstrap.py`` — единственную общую точку сборки.
Дальше — миграция и ваша предметная логика.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).resolve().parent / "module_template"
APP = ROOT / "src" / "app"
MODULES = APP / "modules"
BOOTSTRAP = APP / "bootstrap.py"

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ENTITY_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
RESERVED = {"users", "auth", "shared", "refresh_tokens", "health", "metrics", "metadata", "errors", "api"}
TEST_TEMPLATE = "test_endpoints.py.tmpl"


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


def register(plural: str) -> None:
    """Импорт модуля и строка в ``MODULES``. Импорты потом упорядочит ruff."""
    source = BOOTSTRAP.read_text(encoding="utf-8")
    anchor = "MODULES: tuple[Module, ...] = (\n"
    if anchor not in source:
        sys.exit(f"{BOOTSTRAP.relative_to(ROOT)}: не найден список MODULES")
    imports = list(re.finditer(r"^from app\.modules\.\w+\.module import \w+\n", source, flags=re.M))
    at = imports[-1].end() if imports else source.index("\nMODULES") + 1
    source = source[:at] + f"from app.modules.{plural}.module import {plural}_module\n" + source[at:]
    end = source.index(")\n", source.index(anchor))
    source = source[:end] + f"    {plural}_module,\n" + source[end:]
    BOOTSTRAP.write_text(source, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plural", help="имя модуля во мн. числе, snake_case: projects, task_lists")
    parser.add_argument("entity", nargs="?", help="имя сущности, CamelCase: Project, TaskList")
    args = parser.parse_args()

    plural: str = args.plural
    if not NAME_RE.match(plural) or plural in RESERVED:
        sys.exit(f"Некорректное или зарезервированное имя модуля: {plural!r}")
    entity_cls: str = args.entity or camel(singular(plural))
    if not ENTITY_RE.match(entity_cls):
        sys.exit(f"Некорректное имя сущности: {entity_cls!r}")
    entity = snake(entity_cls)
    if entity == plural:
        sys.exit("Имя модуля (мн. ч.) должно отличаться от имени сущности: укажите сущность явно")

    ctx = {
        "plural": plural,
        "Plural": camel(plural),
        "PLURAL": plural.upper(),
        "entity": entity,
        "Entity": entity_cls,
        "url": plural.replace("_", "-"),
        "Tag": camel(plural),
        "Title": entity.replace("_", " ").capitalize(),
    }

    package = MODULES / plural
    test_file = ROOT / "tests" / "api" / f"test_{plural}_endpoints.py"
    existing = [path for path in (package, test_file) if path.exists()]
    if existing:
        sys.exit("Уже существует: " + ", ".join(str(path.relative_to(ROOT)) for path in existing))

    targets = {
        template: package / template.relative_to(TEMPLATE).with_suffix("")
        for template in sorted(TEMPLATE.rglob("*.tmpl"))
        if template.name != TEST_TEMPLATE
    }
    targets[TEMPLATE / TEST_TEMPLATE] = test_file
    for template, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(template.read_text(encoding="utf-8"), ctx), encoding="utf-8")
    for directory in (package, *(path for path in package.rglob("*") if path.is_dir())):
        (directory / "__init__.py").touch()
    register(plural)

    files = [str(path) for path in (*targets.values(), BOOTSTRAP)]
    # Упорядочить вставленные импорты и привести стиль; без ruff код всё равно рабочий.
    subprocess.run(["uv", "run", "ruff", "check", "--fix", "--quiet", *files], cwd=ROOT, check=False)
    subprocess.run(["uv", "run", "ruff", "format", "--quiet", *files], cwd=ROOT, check=False)
    # docs/openapi.json сверяется с приложением в tests/architecture.
    subprocess.run(["uv", "run", "python", "scripts/export_openapi.py"], cwd=ROOT, check=False)

    print(f"Модуль {plural} (сущность {entity_cls}) создан: /api/v1/{ctx['url']}. Дальше:")
    print(f'  make migration m="add {plural}" && make migrate')
    print(f"  uv run pytest tests/api/test_{plural}_endpoints.py")


if __name__ == "__main__":
    main()
