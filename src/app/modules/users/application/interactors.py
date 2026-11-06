import logging
from dataclasses import dataclass
from typing import Any

from app.modules.users.api.contracts import UserDeactivated, UserInfo
from app.modules.users.application.access import is_admin, require_admin, require_admin_or_self
from app.modules.users.application.dto import UserCreateData, UserUpdateData, to_user_info
from app.modules.users.application.ports import PasswordHasher, UserCriteria, UserGateway
from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole
from app.modules.users.domain.errors import UserAlreadyExistsError, UserNotFoundError
from app.shared.application.changes import apply_changes
from app.shared.application.events import EventPublisher
from app.shared.application.exceptions import DuplicateError
from app.shared.application.pagination import Page, Pagination
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.domain.errors import ForbiddenError
from app.shared.domain.ids import UserId

logger = logging.getLogger(__name__)


@dataclass
class _UserContext:
    uow: UnitOfWork
    user_gateway: UserGateway
    password_hasher: PasswordHasher
    events: EventPublisher

    async def _require_user(self, user_id: UserId) -> User:
        user = await self.user_gateway.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        return user

    async def _add_new_user(self, user: User) -> None:
        if await self.user_gateway.get_by_email(user.email) is not None:
            raise UserAlreadyExistsError(email=user.email)
        await self.uow.add(user)

    async def _commit_new_user(self, user: User) -> None:
        # The pre-check above does not see a concurrent insert; the unique index does.
        try:
            await self.uow.commit()
        except DuplicateError:
            raise UserAlreadyExistsError(email=user.email) from None

    async def _deactivated(self, user: User) -> None:
        """Other modules (``auth``: sessions) react in this same transaction."""
        await self.events.publish(UserDeactivated(user_id=user.id))


class ListUsers(_UserContext):
    async def __call__(self, user_id: UserId, pagination: Pagination, criteria: UserCriteria) -> Page[UserInfo]:
        await require_admin(self.user_gateway, user_id)
        users = await self.user_gateway.get_all(offset=pagination.offset, limit=pagination.limit, criteria=criteria)
        total = await self.user_gateway.count(criteria)
        return Page.build(items=[to_user_info(user) for user in users], total=total, pagination=pagination)


class GetUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId) -> UserInfo:
        await require_admin_or_self(self.user_gateway, user_id, target_id)
        return to_user_info(await self._require_user(target_id))


class GetMe(_UserContext):
    async def __call__(self, user_id: UserId) -> UserInfo:
        return to_user_info(await self._require_user(user_id))


class CreateUser(_UserContext):
    async def __call__(self, user_id: UserId, data: UserCreateData) -> UserInfo:
        await require_admin(self.user_gateway, user_id)
        user = User(
            email=data.email,
            password_hash=self.password_hasher.hash(data.password),
            full_name=data.fullName,
            role=data.role,
            is_active=data.isActive,
            created_by=user_id,
        )
        await self._add_new_user(user)
        result = to_user_info(user)
        await self._commit_new_user(user)
        return result


class UpdateUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId, data: UserUpdateData) -> UserInfo:
        """Anyone may rename themselves; only an admin changes other users, roles and activity."""
        await require_admin_or_self(self.user_gateway, user_id, target_id)
        user = await self._require_user(target_id)
        changes: dict[str, Any] = {"full_name": data.fullName}
        if data.role is not None and data.role != user.role:
            changes["role"] = data.role
        if data.isActive is not None and data.isActive != user.is_active:
            changes["is_active"] = data.isActive
        if changes.keys() != {"full_name"} and not await is_admin(self.user_gateway, user_id):
            raise ForbiddenError
        apply_changes(user, changes)
        if changes.get("is_active") is False:
            await self._deactivated(user)
        result = to_user_info(user)
        await self.uow.commit()
        return result


class DeactivateUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId) -> None:
        """The user stays in the database but loses access and every session."""
        await require_admin(self.user_gateway, user_id)
        user = await self._require_user(target_id)
        apply_changes(user, {"is_active": False})
        await self._deactivated(user)
        await self.uow.commit()


class EnsureAdmin(_UserContext):
    """Creates the admin from the environment on startup unless the email is taken, so it is idempotent."""

    async def __call__(self, email: str, password: str, full_name: str) -> None:
        if await self.user_gateway.get_by_email(email) is not None:
            return
        user = User(
            email=email,
            password_hash=self.password_hasher.hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        user.created_by = user.id
        await self.uow.add(user)
        await self._commit_new_user(user)
        logger.info("admin_created", extra={"user_id": user.id})
