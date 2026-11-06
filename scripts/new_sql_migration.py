"""Новая миграция на чистом SQL.

    uv run python scripts/new_sql_migration.py "add projects"
    make migration-sql m="add projects"                       # то же через make

Создаёт в ``src/alembic/versions/`` три файла со следующим номером, например ``0003``:
``0003_add_projects.py`` (цепочка ревизий, править не нужно), ``0003_add_projects.up.sql`` и
``0003_add_projects.down.sql`` (их заполняете вы). Предыдущая ревизия — текущий head.
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "src" / "alembic.ini"
VERSIONS = ROOT / "src" / "alembic" / "versions"

REVISION_TEMPLATE = '''"""{message}

Revision ID: {revision}
Revises: {down_revision}
Create Date: {created}

The migration itself is SQL: {stem}.up.sql and {stem}.down.sql next to this file.
"""

from collections.abc import Sequence

from app.shared.infra.database.migrations import run_sql

revision: str = "{revision}"
down_revision: str | Sequence[str] | None = {down_literal}
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql(__file__, "up")


def downgrade() -> None:
    run_sql(__file__, "down")
'''

UP_TEMPLATE = """-- {message}
-- PostgreSQL. Runs in the migration's transaction; several statements and $$ bodies are fine.
-- Paste the DDL here: by hand or pgAdmin -> Tools -> Schema Diff -> Generate Script.
-- Then update modules/<module>/infra/tables.py: `alembic check` in CI fails while they disagree.

"""

DOWN_TEMPLATE = """-- {message}: undo {stem}.up.sql, in reverse order.

"""


def slugify(message: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", message.lower()).strip("_")
    if not slug:
        raise ValueError(f"Describe the migration in latin letters or digits: {message!r}")
    return slug[:50].rstrip("_")


def next_number(versions: Path) -> int:
    numbers = [int(m.group(1)) for p in versions.glob("*.py") if (m := re.match(r"^(\d{4})_", p.name))]
    return max(numbers, default=0) + 1


def current_head() -> str | None:
    heads = ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_heads()
    if len(heads) > 1:
        raise ValueError(f"Several heads {heads}: merge them first (alembic merge heads)")
    return heads[0] if heads else None


def create_sql_revision(message: str, versions: Path, down_revision: str | None) -> list[Path]:
    revision = f"{next_number(versions):04d}"
    stem = f"{revision}_{slugify(message)}"
    files = {
        versions / f"{stem}.py": REVISION_TEMPLATE.format(
            message=message,
            revision=revision,
            down_revision=down_revision,
            down_literal="None" if down_revision is None else f'"{down_revision}"',
            created=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            stem=stem,
        ),
        versions / f"{stem}.up.sql": UP_TEMPLATE.format(message=message),
        versions / f"{stem}.down.sql": DOWN_TEMPLATE.format(message=message, stem=stem),
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8", newline="\n")
    return list(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("message", help='что делает миграция, например "add projects"')
    args = parser.parse_args()
    try:
        created = create_sql_revision(args.message, VERSIONS, current_head())
    except ValueError as exc:
        sys.exit(str(exc))
    for path in created:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
