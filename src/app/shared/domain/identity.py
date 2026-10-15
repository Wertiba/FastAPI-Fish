from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.shared.domain.errors import AccessDeniedError


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


@dataclass(frozen=True, slots=True)
class Identity:
    user_id: UUID
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    def require_admin(self) -> None:
        if not self.is_admin:
            raise AccessDeniedError

    def require_admin_or_self(self, user_id: UUID) -> None:
        if not self.is_admin and self.user_id != user_id:
            raise AccessDeniedError
