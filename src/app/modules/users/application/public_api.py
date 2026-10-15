from uuid import UUID

from app.modules.users.application.ports import PasswordHasher, UserRepository
from app.modules.users.application.registrar import UserRegistrar
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import UserInactiveError
from app.modules.users.public import UserInfo, UsersApi
from app.shared.domain.errors import AuthenticationError


def to_user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_by=user.created_by,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class UsersApiImpl(UsersApi):
    _dummy_hash: str | None = None

    def __init__(self, users: UserRepository, registrar: UserRegistrar, hasher: PasswordHasher) -> None:
        self._users = users
        self._registrar = registrar
        self._hasher = hasher

    async def get_user(self, user_id: UUID) -> UserInfo | None:
        user = await self._users.get_by_id(user_id)
        return None if user is None else to_user_info(user)

    async def register(self, *, email: str, password: str, full_name: str) -> UserInfo:
        user = await self._registrar.register(email=email, password=password, full_name=full_name)
        return to_user_info(user)

    async def authenticate(self, *, email: str, password: str) -> UserInfo:
        user = await self._users.get_by_email(email)
        if user is None:
            # Тратим столько же времени, сколько на проверку настоящего хеша,
            # чтобы по задержке ответа нельзя было перебирать существующие email.
            self._hasher.verify(password, self._get_dummy_hash())
            raise AuthenticationError
        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError
        if not user.is_active:
            raise UserInactiveError
        return to_user_info(user)

    def _get_dummy_hash(self) -> str:
        if UsersApiImpl._dummy_hash is None:
            UsersApiImpl._dummy_hash = self._hasher.hash("dummy-password-for-timing-1")
        return UsersApiImpl._dummy_hash
