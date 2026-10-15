"""Запросы: только читают, ничего не коммитят."""

from uuid import UUID

from app.modules.users.application.ports import UserFilter, UserRepository
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import UserNotFoundError
from app.shared.application.identity import IdentityProvider
from app.shared.application.pagination import Page, Pagination


class GetUser:
    def __init__(self, idp: IdentityProvider, users: UserRepository) -> None:
        self._idp = idp
        self._users = users

    async def __call__(self, user_id: UUID) -> User:
        (await self._idp.get_identity()).require_admin_or_self(user_id)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        return user


class GetCurrentUser:
    def __init__(self, idp: IdentityProvider, users: UserRepository) -> None:
        self._idp = idp
        self._users = users

    async def __call__(self) -> User:
        identity = await self._idp.get_identity()
        user = await self._users.get_by_id(identity.user_id)
        if user is None:
            raise UserNotFoundError
        return user


class ListUsers:
    def __init__(self, idp: IdentityProvider, users: UserRepository) -> None:
        self._idp = idp
        self._users = users

    async def __call__(self, filters: UserFilter, pagination: Pagination) -> Page[User]:
        (await self._idp.get_identity()).require_admin()
        items = await self._users.find(filters, pagination)
        total = await self._users.count(filters)
        return Page(items=items, total=total, page=pagination.page, size=pagination.size)
