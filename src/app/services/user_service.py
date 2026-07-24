from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions.user_exs import (
    ForbiddenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.schemas.role import RoleCode, RoleRead
from app.core.schemas.user import (
    ApproverAssignBody,
    ApproverReadResponse,
    TokenData,
    UserCreateBody,
    UserReadResponse,
    UserUpdateBody,
)
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import Approver, Role, User
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import JWTService


class UserService:
    def __init__(self, uow: UnitOfWork, jwt_service: JWTService):
        self.uow = uow
        self.jwt_service = jwt_service

    @staticmethod
    def _convert_to_response(user: User) -> UserReadResponse:
        return UserReadResponse(
            roles=[
                RoleRead(
                    id=role.id,
                    code=RoleCode(role.code),
                    value=role.value,
                    description=role.description,
                )
                for role in user.roles
            ],
            **user.model_dump(exclude={"roles"})
        )

    @staticmethod
    def _is_admin(user_roles: list[RoleCode]) -> bool:
        return RoleCode.ADMN in user_roles

    async def _calculate_required(self):
        async with self.uow:
            count = await self.uow.user_repo.count()
            return count // 2 + 1

    async def _validate_roles(self, role_codes: list[str] | None) -> list[Role] | None:
        if role_codes is None:
            return None

        roles = await self.uow.role_repo.get_by_codes(role_codes)

        if len(roles) != len(role_codes):
            found_codes = {role.code for role in roles}
            missing = set(role_codes) - found_codes
            raise ValueError(f"Роли не найдены: {', '.join(missing)}")
        return roles

    async def register(self, user_data: UserCreateBody) -> UserReadResponse:
        async with self.uow:
            existing_user = await self.uow.user_repo.get_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError

            user_data.password = self.jwt_service.get_password_hash(user_data.password)
            role_codes = [code.value for code in user_data.roles] if user_data.roles is not None else None
            roles = await self._validate_roles(role_codes)

            user = User(**user_data.model_dump(exclude={"roles"}))
            created_user = await self.uow.user_repo.add(user)
            if roles:
                await self.uow.user_repo.set_roles(created_user.id, [role.id for role in roles])

            user_with_roles = await self.uow.user_repo.get_by_id(created_user.id)
            return self._convert_to_response(user_with_roles)

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

    async def get_current_by_id(self, user_data: TokenData, user_id: UUID) -> UserReadResponse:
        user = await self.get_by_id(user_id)

        if self._is_admin([r.code for r in user.roles]):
            return user

        if user_data.id != user_id:
            raise ForbiddenError
        return user

    async def deactivate(self, user_id: UUID) -> None:
        async with self.uow:
            if await self.get_by_id(user_id):
                return await self.uow.user_repo.deactivate(user_id, isActive=False, updatedAt=datetime.now(tz=UTC))
            raise UserNotFoundError

    async def update(
            self, user_id: UUID, current_user_roles: list[RoleCode], new_data: UserUpdateBody
    ) -> UserReadResponse:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError

            is_admin = self._is_admin(current_user_roles)

            if not is_admin:
                if new_data.roles is not None or new_data.isActive is not None:
                    raise ForbiddenError

            new_roles = new_data.roles if (is_admin and new_data.roles is not None) else None

            if is_admin and new_roles is not None:
                role_codes = [code.value for code in new_roles] # noqa
                roles = await self._validate_roles(role_codes)
                await self.uow.user_repo.set_roles(user_id, [role.id for role in roles])

            if not (is_admin and new_data.isActive is not None):
                new_data.isActive = user.isActive

            payload = new_data.model_dump(
                exclude_unset=True,
                exclude={"roles"},
            )

            updated_user = await self.uow.user_repo.update(user_id, payload)
            return self._convert_to_response(updated_user)

    async def update_me(self, user_data: TokenData, new_data: UserUpdateBody) -> UserReadResponse:
        return await self.update(user_data.id, user_data.roles, new_data)

    async def update_current(
            self, user_id: UUID, user_data: TokenData, new_data: UserUpdateBody
    ) -> UserReadResponse:
        is_admin = self._is_admin(user_data.roles)

        if not is_admin and user_id != user_data.id:
            raise ForbiddenError

        await self.get_by_id(user_id)
        return await self.update(user_id, user_data.roles, new_data)

    async def assign_approver(self, user_data: TokenData, approver_data: ApproverAssignBody) -> ApproverReadResponse:
        async with self.uow:
            if await self.uow.approver_repo.get_by_two_ids(approver_data.experimenter_id, approver_data.approver_id):
                raise UserAlreadyExistsError

            if await self.uow.user_repo.get_by_id(
                    approver_data.approver_id
            ) and await self.uow.user_repo.get_by_id(
                approver_data.experimenter_id
            ):
                approver = await self.uow.approver_repo.add(Approver(
                    **approver_data.model_dump(),
                    addedBy=user_data.id,
                ))
                return ApproverReadResponse(**approver.model_dump(exclude={"experimenter", "approver", "reviews"}))
        raise UserNotFoundError

    async def get_approver(self, id_: UUID) -> ApproverReadResponse | None:
        async with self.uow:
            result = await self.uow.approver_repo.get_by_id(id_)
            if not result:
                raise UserNotFoundError
            return ApproverReadResponse(**result.model_dump())

    async def del_approver(self, id_: UUID) -> None:
        async with self.uow:
            result = await self.uow.approver_repo.get_by_id(id_)
            if result:
                await self.uow.approver_repo.deactivate(id_, isActive=False)
                return
            raise UserNotFoundError
