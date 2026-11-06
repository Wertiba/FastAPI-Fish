"""SQL revisions: the generator and the whole chain in Alembic's offline mode (``upgrade --sql``, no database)."""

import io
import shutil
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.shared.infra.database.migrations import has_statements, sql_path
from scripts.new_sql_migration import VERSIONS, create_sql_revision, current_head, slugify

ALEMBIC = Path(__file__).parents[2] / "src" / "alembic"

UP_SQL = """-- comments are kept
CREATE TABLE projects (id uuid PRIMARY KEY, name varchar(200) NOT NULL);
CREATE FUNCTION touch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.name := trim(NEW.name);
    RETURN NEW;
END;
$$;
"""


def test_names() -> None:
    assert slugify("Add projects + tags!") == "add_projects_tags"
    with pytest.raises(ValueError, match="latin"):
        slugify("проекты")
    assert sql_path("/v/0003_add.py", "down") == Path("/v/0003_add.down.sql")
    assert not has_statements("-- only a comment\n\n")
    assert has_statements("-- a comment\nDROP TABLE x;")


def test_the_new_revision_follows_the_head(tmp_path: Path) -> None:
    (tmp_path / "0001_a.py").touch()
    (tmp_path / "0007_b.py").touch()
    created = create_sql_revision("add projects", tmp_path, "0007")
    assert [p.name for p in created] == ["0008_add_projects.py", "0008_add_projects.up.sql", "0008_add_projects.down.sql"]
    revision = created[0].read_text(encoding="utf-8")
    assert 'revision: str = "0008"' in revision
    assert 'down_revision: str | Sequence[str] | None = "0007"' in revision
    assert current_head() is not None  # the repository's own chain has exactly one head


def offline(versions: Path, action: str, target: str) -> str:
    output = io.StringIO()
    config = Config(output_buffer=output)  # no ini file: env.py leaves the test logging alone
    config.set_main_option("script_location", str(ALEMBIC))
    config.set_main_option("path_separator", "os")
    config.set_main_option("version_locations", str(versions))
    getattr(command, action)(config, target, sql=True)
    return output.getvalue()


def test_sql_revision_runs_in_the_chain(tmp_path: Path) -> None:
    for revision in VERSIONS.glob("*.py"):
        shutil.copy(revision, tmp_path)
    head = current_head()
    _, up, down = create_sql_revision("add projects", tmp_path, head)
    up.write_text(UP_SQL, encoding="utf-8")
    down.write_text("DROP FUNCTION touch();\nDROP TABLE projects;\n", encoding="utf-8")
    new = up.name.split("_")[0]

    upgrade = offline(tmp_path, "upgrade", f"{head}:head")
    assert "CREATE TABLE projects" in upgrade
    assert "NEW.name := trim(NEW.name);" in upgrade  # the $$ body reaches the database untouched
    assert f"UPDATE alembic_version SET version_num='{new}'" in upgrade

    downgrade = offline(tmp_path, "downgrade", f"{new}:{head}")
    assert downgrade.index("DROP FUNCTION touch();") < downgrade.index("DROP TABLE projects;")
