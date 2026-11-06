from dataclasses import dataclass

from app.modules.users.api.contracts import UserInfo
from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole


@dataclass(kw_only=True)
class UserCreateData:
    email: str
    password: str
    fullName: str
    role: UserRole = UserRole.USER
    isActive: bool = True


@dataclass(kw_only=True)
class UserUpdateData:
    fullName: str
    role: UserRole | None = None
    isActive: bool | None = None


def to_user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        isActive=user.is_active,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
        createdBy=user.created_by or user.id,
    )
