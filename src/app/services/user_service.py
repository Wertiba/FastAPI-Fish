from datetime import UTC, datetime
from uuid import UUID

from app.core.enums import UserRole
from app.core.exceptions.base import DuplicateError
from app.core.exceptions.user_exs import ForbiddenError, UserAlreadyExistsError, UserNotFoundError
from app.core.schemas.user import (
    AdminRegisterUserBody,
    UserData,
    UserFilterQuery,
    UserReadResponse,
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
    def _to_read_response(user: User) -> UserReadResponse:
        return UserReadResponse(
            id=user.id,
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
            createdBy=user.created_by,
        )

    async def get_all_users(self, pagination: PaginationParams, filters: UserFilterQuery) -> Page[UserReadResponse]:
        async with self.uow:
            users = await self.uow.user_repo.get_filtered(filters, offset=pagination.offset, limit=pagination.limit)
            total = await self.uow.user_repo.count_filtered(filters)
            items = [self._to_read_response(u) for u in users]
            return Page.build(items=items, total=total, pagination=pagination)

    async def get_by_id(self, user_id: UUID) -> UserReadResponse:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError
            return self._to_read_response(user)

    async def create_user(self, data: AdminRegisterUserBody) -> UserReadResponse:
        async with self.uow:
            existing = await self.uow.user_repo.get_by_email(data.email)
            if existing:
                raise UserAlreadyExistsError

            hashed_password = self.jwt_service.get_password_hash(data.password)
            try:
                user = await self.uow.user_repo.add(
                    User(
                        email=data.email,
                        password=hashed_password,
                        full_name=data.fullName,
                        role=data.role,
                        is_active=data.isActive,
                    )
                )
            except DuplicateError:
                raise UserAlreadyExistsError from None
            user = await self.uow.user_repo.update(user.id, {"created_by": user.id})
            return self._to_read_response(user)

    async def update_user(self, user_id: UUID, new_data: UserUpdateBody, acting_user: UserData) -> UserReadResponse:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError

            is_admin = acting_user.role == UserRole.ADMIN
            new_role = new_data.role if new_data.role is not None else user.role
            new_is_active = new_data.isActive if new_data.isActive is not None else user.is_active

            if not is_admin and (new_role != user.role or new_is_active != user.is_active):
                raise ForbiddenError

            was_active = user.is_active
            updated_user = await self.uow.user_repo.update(
                user_id, {"full_name": new_data.fullName, "role": new_role, "is_active": new_is_active}
            )

            if was_active and not new_is_active:
                await self.uow.refresh_token_repo.delete_all_for_user(user_id)

            return self._to_read_response(updated_user)

    async def deactivate_by_id(self, user_id: UUID) -> None:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError

            await self.uow.user_repo.deactivate(user_id, is_active=False, updated_at=datetime.now(UTC))
            await self.uow.refresh_token_repo.delete_all_for_user(user_id)
