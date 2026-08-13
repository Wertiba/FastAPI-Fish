import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_bash() -> str | None:
    # On Windows, plain "bash" on PATH can resolve to the WSL launcher shim
    # (System32\bash.exe), which can't see Windows-style paths at all. Prefer
    # a real Git-for-Windows bash when one is installed.
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


BASH = _find_bash()


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "configs").mkdir(parents=True)
    (repo / "actions").mkdir()

    shutil.copy(REPO_ROOT / "src" / "configs" / "config.yaml", repo / "src" / "configs" / "config.yaml")
    shutil.copy(REPO_ROOT / "src" / ".env.example", repo / "src" / ".env.example")
    shutil.copy(REPO_ROOT / "docker-compose.yml", repo / "docker-compose.yml")
    shutil.copy(REPO_ROOT / "actions" / "init-project.sh", repo / "actions" / "init-project.sh")

    return repo


@pytest.mark.skipif(BASH is None, reason="bash not available on this machine")
def test_init_project_sh_renames_app_name_slug_db_and_volume(tmp_path):
    repo = _fixture_repo(tmp_path)

    result = subprocess.run(
        [BASH, (repo / "actions" / "init-project.sh").as_posix(), "Orders"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    config_text = (repo / "src" / "configs" / "config.yaml").read_text(encoding="utf-8")
    assert "name: Orders" in config_text
    assert "path: logs/orders.log" in config_text

    env_text = (repo / "src" / ".env.example").read_text(encoding="utf-8")
    assert "DB_NAME=orders" in env_text
    assert "POSTGRES_DB=orders" in env_text

    compose_text = (repo / "docker-compose.yml").read_text(encoding="utf-8")
    assert "orders_db_data:" in compose_text
    assert "- orders_db_data:/var/lib/postgresql/data" in compose_text


@pytest.mark.skipif(BASH is None, reason="bash not available on this machine")
def test_init_project_sh_requires_exactly_one_argument(tmp_path):
    repo = _fixture_repo(tmp_path)

    result = subprocess.run(
        [BASH, (repo / "actions" / "init-project.sh").as_posix()],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
