"""``python -m app`` — локальный запуск с autoreload."""

import uvicorn

from app.bootstrap.config import Settings


def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    uvicorn.run("app.main:create_app", factory=True, host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":
    main()
