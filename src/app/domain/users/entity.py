from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.users.enums import UserRole
from app.domain.users.ids import UserId


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False, kw_only=True)
class User:
    id: UserId = field(default_factory=uuid4)
    email: str
    password_hash: str
    full_name: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_by: UserId | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
