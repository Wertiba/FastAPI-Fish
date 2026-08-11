import uuid

import pytest

from app.api.v1.dependencies.current_user import get_admin_or_self_user, get_admin_user
from app.core.exceptions.user_exs import ForbiddenError
from app.core.schemas.user import UserData, UserRole


def _user(role: UserRole, user_id: uuid.UUID | None = None) -> UserData:
    uid = user_id or uuid.uuid4()
    return UserData(
        id=uid,
        email="u@fish.io",
        fullName="U",
        role=role,
        isActive=True,
        createdAt="2026-01-01T00:00:00Z",
        updatedAt="2026-01-01T00:00:00Z",
        createdBy=uid,
    )


async def test_admin_user_dep_allows_admin():
    admin = _user(UserRole.ADMIN)
    assert await get_admin_user(admin) == admin


async def test_admin_user_dep_rejects_non_admin():
    user = _user(UserRole.USER)
    with pytest.raises(ForbiddenError):
        await get_admin_user(user)


async def test_admin_or_self_allows_admin_for_any_id():
    admin = _user(UserRole.ADMIN)
    other_id = uuid.uuid4()
    assert await get_admin_or_self_user(other_id, admin) == admin


async def test_admin_or_self_allows_self():
    user = _user(UserRole.USER)
    assert await get_admin_or_self_user(user.id, user) == user


async def test_admin_or_self_rejects_other_user():
    user = _user(UserRole.USER)
    other_id = uuid.uuid4()
    with pytest.raises(ForbiddenError):
        await get_admin_or_self_user(other_id, user)
