from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.shared.domain.errors import AccessDeniedError
from app.shared.domain.identity import Identity, UserRole
from app.shared.domain.time import utc_now


@dataclass(kw_only=True, eq=False)
class User:
    """Чистая доменная сущность. К таблице привязывается в ``infrastructure/tables.py``."""

    id: UUID
    email: str
    password_hash: str
    full_name: str
    role: UserRole
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        created_by: UUID | None = None,
    ) -> "User":
        user_id = uuid4()
        now = utc_now()
        return cls(
            id=user_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
            created_by=created_by or user_id,
            created_at=now,
            updated_at=now,
        )

    def update(
        self, *, full_name: str, role: UserRole | None, is_active: bool | None, actor: Identity
    ) -> bool:
        """Меняет профиль. Роль и активность может менять только админ.

        Возвращает ``True``, если пользователь был деактивирован этим изменением.
        """
        new_role = self.role if role is None else role
        new_is_active = self.is_active if is_active is None else is_active
        if not actor.is_admin and (new_role != self.role or new_is_active != self.is_active):
            raise AccessDeniedError

        was_active = self.is_active
        self.full_name = full_name
        self.role = new_role
        self.is_active = new_is_active
        self.updated_at = utc_now()
        return was_active and not new_is_active

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = utc_now()
