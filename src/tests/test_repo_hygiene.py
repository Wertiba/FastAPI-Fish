# src/tests/test_repo_hygiene.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_garbage_files_are_gone():
    assert not (REPO_ROOT / "server.pas").exists()
    assert not (REPO_ROOT / "src" / "tests" / "LottyABPlatform.postman_collection.json").exists()
    assert not (REPO_ROOT / "src" / "tests" / "test_auth_and_users.py").exists()


def test_requirements_txt_is_utf8_and_pruned():
    text = (REPO_ROOT / "src" / "requirements.txt").read_text(encoding="utf-8")
    for banned in ("aioredis", "fastapi-cache2", "hiredis", "sentry-sdk", "pendulum", "fastar", "fastapi-swagger-dark"):
        assert banned not in text, f"{banned} should have been pruned"
    assert "SQLAlchemy" in text


def test_config_yaml_has_no_unrelated_project_cruft():
    text = (REPO_ROOT / "src" / "configs" / "config.yaml").read_text(encoding="utf-8")
    assert "NoteManager" not in text
    assert "exp_index" not in text
    assert "restrictions" not in text
    assert "cache" not in text.split("token:")[0]  # crude but sufficient: no top-level cache: block
