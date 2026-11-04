from pathlib import Path

from dynaconf import Dynaconf
from sqlalchemy.engine import make_url

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
    url = make_url(str(settings.DB_URL).removeprefix("jdbc:")).set(drivername=settings.db.driver)
    if settings.get("DB_USER"):
        url = url.set(username=str(settings.DB_USER))
    if settings.get("DB_PASSWORD"):
        url = url.set(password=str(settings.DB_PASSWORD))
    return url.render_as_string(hide_password=False)


settings.set("POSTGRES_URL", build_postgres_url())
