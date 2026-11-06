from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from app.modules.users.domain.enums import UserRole
from app.shared.domain.ids import UserId
from app.shared.domain.time import utc_now


@dataclass(eq=False, kw_only=True)
class User:
    id: UserId = field(default_factory=uuid4)
    email: str
    password_hash: str
    full_name: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_by: UserId | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
