from dataclasses import dataclass
from datetime import datetime

from app.domain.users.entity import User
from app.domain.users.enums import UserRole
from app.domain.users.ids import UserId


@dataclass(kw_only=True)
class UserRegisterData:
    email: str
    password: str
    fullName: str


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


@dataclass(kw_only=True)
class UserLoginData:
    email: str
    password: str


@dataclass(kw_only=True)
class UserData:
    """The authenticated user behind the current request."""

    id: UserId
    email: str
    fullName: str
    role: UserRole
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
    createdBy: UserId


@dataclass(kw_only=True)
class UserResult:
    id: UserId
    email: str
    fullName: str
    role: UserRole
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
    createdBy: UserId


@dataclass(kw_only=True)
class UserAndAccessTokenResult:
    accessToken: str
    expiresIn: int
    user: UserResult


def to_user_result(user: User) -> UserResult:
    return UserResult(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        isActive=user.is_active,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
        createdBy=user.created_by or user.id,
    )
