from uuid import UUID

from app.modules.users.application.ports import PasswordHasher, UserRepository
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import EmailAlreadyExistsError
from app.shared.domain.identity import UserRole


class UserRegistrar:
    """Общая логика создания пользователя: уникальность email + хеш пароля.

    Используется админским CreateUser, саморегистрацией (UsersApi) и EnsureAdmin.
    """

    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        created_by: UUID | None = None,
    ) -> User:
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyExistsError(email)
        user = User.create(
            email=email,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
            role=role,
            is_active=is_active,
            created_by=created_by,
        )
        await self._users.add(user)
        return user
