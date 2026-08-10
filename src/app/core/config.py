from pathlib import Path

from dynaconf import Dynaconf

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "configs" / "config.yaml"
ENV_FILE = BASE_DIR / ".env"


settings = Dynaconf(
    envvar_prefix=False,
    settings_files=[CONFIG_FILE],
    load_dotenv=True,
    dotenv_path=ENV_FILE,
    environments=False,
    merge_enabled=True,
    lowercase_read=True,
)


def build_postgres_url() -> str:
    # Build URL from settings, with defaults for missing values
    db_user = settings.get("db_user", "postgres")
    db_password = settings.get("db_password", "postgres")
    db_host = settings.get("db_host", "localhost")
    db_port = settings.get("db_port", "5432")
    db_name = settings.get("db_name", "fastapi_fish")

    return (
        f"{settings.db.driver}://"
        f"{db_user}:"
        f"{db_password}@"
        f"{db_host}:"
        f"{db_port}/"
        f"{db_name}"
    )


settings.set("POSTGRES_URL", build_postgres_url())
