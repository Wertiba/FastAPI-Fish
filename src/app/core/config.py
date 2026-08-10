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
    return (
        f"{settings.db.driver}://"
        f"{settings.db_user}:"
        f"{settings.db_password}@"
        f"{settings.db_host}:"
        f"{settings.db_port}/"
        f"{settings.db_name}"
    )


settings.set("POSTGRES_URL", build_postgres_url())
