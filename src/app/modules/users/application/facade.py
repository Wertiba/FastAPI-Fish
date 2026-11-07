from dataclasses import dataclass

from app.modules.users.api.contracts import UserInfo, UsersFacade
from app.modules.users.application.access import is_admin
from app.modules.users.application.dto import to_user_info
from app.modules.users.application.ports import PasswordHasher, UserGateway
from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole
from app.modules.users.domain.errors import UserAlreadyExistsError
from app.shared.application.exceptions import DuplicateError
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.domain.ids import UserId


@dataclass
class UsersFacadeImpl(UsersFacade):
    """What other modules may do with users: the implementation of ``users.api.contracts.UsersFacade``."""

    uow: UnitOfWork
    user_gateway: UserGateway
    password_hasher: PasswordHasher

    async def get(self, user_id: UserId) -> UserInfo | None:
        user = await self.user_gateway.get_by_id(user_id)
        return None if user is None else to_user_info(user)

    async def check_credentials(self, email: str, password: str) -> UserInfo | None:
        user = await self.user_gateway.get_by_email(email)
        if user is None:
            self.password_hasher.verify_dummy(password)
            return None
        if not self.password_hasher.verify(password, user.password_hash):
            return None
        return to_user_info(user)

    async def register(self, *, email: str, password: str, full_name: str) -> UserInfo:
        if await self.user_gateway.get_by_email(email) is not None:
            raise UserAlreadyExistsError(email=email)
        user = User(
            email=email,
            password_hash=self.password_hasher.hash(password),
            full_name=full_name,
            role=UserRole.USER,
            is_active=True,
        )
        user.created_by = user.id
        await self.uow.add(user)
        # Modules share no ORM relationships, so SQLAlchemy cannot order INSERTs across them:
        # flush now so rows of other modules (e.g. refresh tokens) can reference the user by FK.
        try:
            await self.uow.flush()
        except DuplicateError:
            raise UserAlreadyExistsError(email=email) from None
        return to_user_info(user)

    async def is_admin(self, user_id: UserId) -> bool:
        return await is_admin(self.user_gateway, user_id)
