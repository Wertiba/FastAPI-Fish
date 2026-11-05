import logging
from dataclasses import dataclass
from typing import Any

from app.application.changes import apply_changes
from app.application.exceptions import DuplicateError
from app.application.pagination import Page, Pagination
from app.application.ports.refresh_token_gateway import RefreshTokenGateway
from app.application.ports.tokens import TokenService
from app.application.ports.unit_of_work import UnitOfWork
from app.application.ports.user_gateway import UserCriteria, UserGateway
from app.application.users.access import is_admin, require_admin, require_admin_or_self
from app.application.users.dto import UserCreateData, UserResult, UserUpdateData, to_user_result
from app.domain.users.entity import User
from app.domain.users.enums import UserRole
from app.domain.users.errors import ForbiddenError, UserAlreadyExistsError, UserNotFoundError
from app.domain.users.ids import UserId

logger = logging.getLogger(__name__)


@dataclass
class _UserContext:
    uow: UnitOfWork
    user_gateway: UserGateway
    refresh_token_gateway: RefreshTokenGateway
    jwt_service: TokenService

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


class ListUsers(_UserContext):
    async def __call__(self, user_id: UserId, pagination: Pagination, criteria: UserCriteria) -> Page[UserResult]:
        await require_admin(self.user_gateway, user_id)
        users = await self.user_gateway.get_all(offset=pagination.offset, limit=pagination.limit, criteria=criteria)
        total = await self.user_gateway.count(criteria)
        return Page.build(items=[to_user_result(user) for user in users], total=total, pagination=pagination)


class GetUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId) -> UserResult:
        await require_admin_or_self(self.user_gateway, user_id, target_id)
        return to_user_result(await self._require_user(target_id))


class GetMe(_UserContext):
    async def __call__(self, user_id: UserId) -> UserResult:
        return to_user_result(await self._require_user(user_id))


class CreateUser(_UserContext):
    async def __call__(self, user_id: UserId, data: UserCreateData) -> UserResult:
        await require_admin(self.user_gateway, user_id)
        user = User(
            email=data.email,
            password_hash=self.jwt_service.get_password_hash(data.password),
            full_name=data.fullName,
            role=data.role,
            is_active=data.isActive,
            created_by=user_id,
        )
        await self._add_new_user(user)
        result = to_user_result(user)
        await self._commit_new_user(user)
        return result


class UpdateUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId, data: UserUpdateData) -> UserResult:
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
            await self.refresh_token_gateway.delete_by_user(user.id)
        result = to_user_result(user)
        await self.uow.commit()
        return result


class DeactivateUser(_UserContext):
    async def __call__(self, user_id: UserId, target_id: UserId) -> None:
        """The user stays in the database but loses access and every session."""
        await require_admin(self.user_gateway, user_id)
        user = await self._require_user(target_id)
        apply_changes(user, {"is_active": False})
        await self.refresh_token_gateway.delete_by_user(user.id)
        await self.uow.commit()


class EnsureAdmin(_UserContext):
    """Creates the admin from the environment on startup unless the email is taken, so it is idempotent."""

    async def __call__(self, email: str, password: str, full_name: str) -> None:
        if await self.user_gateway.get_by_email(email) is not None:
            return
        user = User(
            email=email,
            password_hash=self.jwt_service.get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        user.created_by = user.id
        await self.uow.add(user)
        await self._commit_new_user(user)
        logger.info("admin_created", extra={"user_id": user.id})
