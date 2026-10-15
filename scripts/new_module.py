"""Генератор нового доменного модуля с рабочим CRUD.

    uv run python scripts/new_module.py projects             # сущность Project (угадывается)
    uv run python scripts/new_module.py task_lists TaskList  # сущность указана явно
    make module name=projects                                # то же через make

Создаёт ``src/app/modules/<module>/`` (domain/application/infrastructure/presentation,
ioc, module, public), e2e-тест ``tests/e2e/test_<module>.py`` и регистрирует модуль
в ``src/app/modules/registry.py``. Дальше — миграция и ваша предметная логика.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).resolve().parent / "module_template"
MODULES = ROOT / "src" / "app" / "modules"
REGISTRY = MODULES / "registry.py"
TESTS = ROOT / "tests" / "e2e"

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ENTITY_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
RESERVED = {"users", "auth", "shared", "registry", "health", "metrics"}


def camel(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


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


def register(module: str) -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    import_line = f"from app.modules.{module}.module import {module}_module\n"
    if import_line in source:
        return
    # импорт — после последнего импорта модулей, запись — перед закрывающей скобкой MODULES
    last_import = list(re.finditer(r"^from app\.modules\..+\n", source, flags=re.M))[-1]
    source = source[: last_import.end()] + import_line + source[last_import.end() :]
    closing = source.rindex(")")
    source = source[:closing] + f"    {module}_module,\n" + source[closing:]
    REGISTRY.write_text(source, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("module", help="имя модуля во мн. числе, snake_case: projects, task_lists")
    parser.add_argument("entity", nargs="?", help="имя сущности, CamelCase: Project, TaskList")
    args = parser.parse_args()

    module: str = args.module
    if not NAME_RE.match(module) or module in RESERVED:
        sys.exit(f"Некорректное или зарезервированное имя модуля: {module!r}")
    entity_cls: str = args.entity or camel(singular(module))
    if not ENTITY_RE.match(entity_cls):
        sys.exit(f"Некорректное имя сущности: {entity_cls!r}")
    entity = snake(entity_cls)
    if entity == module:
        sys.exit("Имя модуля должно отличаться от сущности (используйте мн. число: projects / Project)")

    target = MODULES / module
    if target.exists():
        sys.exit(f"Модуль уже существует: {target.relative_to(ROOT)}")

    ctx = {
        "module": module,
        "Module": camel(module),
        "entity": entity,
        "Entity": entity_cls,
        "url": module.replace("_", "-"),
        "Title": module.replace("_", " ").title(),
    }

    created: list[Path] = []
    for tmpl in sorted(TEMPLATE.rglob("*.tmpl")):
        if tmpl.name == "test_module.py.tmpl":
            out = TESTS / f"test_{module}.py"
        else:
            out = target / tmpl.relative_to(TEMPLATE).with_suffix("")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(tmpl.read_text(encoding="utf-8"), ctx), encoding="utf-8")
        created.append(out)

    for package in [target, *(p for p in target.iterdir() if p.is_dir())]:
        (package / "__init__.py").touch()

    register(module)
    paths = [str(target), str(REGISTRY), *map(str, created)]
    ruff = [sys.executable, "-m", "ruff"]  # ruff из того же окружения, PATH не нужен
    subprocess.run([*ruff, "check", "-q", "--fix", "--select", "I", *paths], check=False, cwd=ROOT)
    subprocess.run([*ruff, "format", "-q", *paths], check=False, cwd=ROOT)

    print(f"Модуль {module!r} (сущность {entity_cls}) создан:")
    for path in created:
        print("  +", path.relative_to(ROOT))
    print(f"  ~ {REGISTRY.relative_to(ROOT)}")
    print(
        "\nДальше:\n"
        f'  make migration m="add {module}"\n'
        "  make migrate\n"
        f"  uv run pytest tests/e2e/test_{module}.py"
    )


if __name__ == "__main__":
    main()
