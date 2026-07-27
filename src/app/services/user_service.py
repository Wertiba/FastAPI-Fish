from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions.user_exs import (
    ForbiddenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.schemas.user import (
    TokenData,
    UserCreateBody,
    UserReadResponse,
    UserRole,
    UserUpdateBody,
)
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import User
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import JWTService


class UserService:
    def __init__(self, uow: UnitOfWork, jwt_service: JWTService):
        self.uow = uow
        self.jwt_service = jwt_service

    @staticmethod
    def _convert_to_response(user: User) -> UserReadResponse:
        return UserReadResponse(**user.model_dump())

    @staticmethod
    def _is_admin(role: UserRole) -> bool:
        return role == UserRole.ADMN

    async def register(self, user_data: UserCreateBody) -> UserReadResponse:
        async with self.uow:
            existing_user = await self.uow.user_repo.get_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError

            user_data.password = self.jwt_service.get_password_hash(user_data.password)
            user = await self.uow.user_repo.add(User(**user_data.model_dump()))
            return self._convert_to_response(user)

    async def get_all_users(self, pagination: PaginationParams) -> Page[UserReadResponse]:
        async with self.uow:
            users = await self.uow.user_repo.get_paginated(offset=pagination.offset, limit=pagination.limit)
            valid = [self._convert_to_response(u) for u in users]
            total = await self.uow.user_repo.count()
            return Page.build(items=valid, total=total, pagination=pagination)

    async def get_by_id(self, user_id: UUID) -> UserReadResponse | None:
        async with self.uow:
            user_exists = await self.uow.user_repo.get_by_id(user_id)
            if not user_exists:
                raise UserNotFoundError

            return self._convert_to_response(user_exists)

    async def deactivate_by_id(self, user_id: UUID) -> None:
        async with self.uow:
            await self.get_by_id(user_id)
            return await self.uow.user_repo.deactivate(user_id, isActive=False, updatedAt=datetime.now(tz=UTC))

    async def update_by_id(self, user_id: UUID, new_data: UserUpdateBody) -> UserReadResponse:
        async with self.uow:
            await self.uow.user_repo.get_by_id(user_id)

            updated_user = await self.uow.user_repo.update(user_id, new_data.model_dump())
            return self._convert_to_response(updated_user)
