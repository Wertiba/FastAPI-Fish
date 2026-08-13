# src/tests/test_app_boot.py
from fastapi.testclient import TestClient

from app.main import app


def test_app_imports_and_ping_responds():
    client = TestClient(app)
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_admin_bootstrap_runs_on_startup(client, db_session_factory):
    from sqlalchemy import select

    from app.core.config import settings
    from app.infrastructure.models import User

    async with db_session_factory() as session:
        result = await session.execute(select(User).where(User.email == settings.APP_ADMIN_EMAIL))
        admin = result.scalar_one_or_none()

    assert admin is not None
    assert admin.role == "ADMIN"


def test_user_role_has_no_typo():
    from app.core.schemas.user import UserRole

    assert UserRole.ADMIN.value == "ADMIN"
    assert not hasattr(UserRole, "ADMN")
