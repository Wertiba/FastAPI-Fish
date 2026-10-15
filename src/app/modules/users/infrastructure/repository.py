from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.application.ports import UserFilter, UserRepository
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import EmailAlreadyExistsError
from app.modules.users.infrastructure.tables import users_table as t
from app.shared.application.pagination import Pagination


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyExistsError(user.email) from exc

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.scalars(sa.select(User).where(t.c.email == email))
        return result.one_or_none()

    async def find(self, filters: UserFilter, pagination: Pagination) -> list[User]:
        stmt = (
            sa.select(User)
            .where(*self._conditions(filters))
            .order_by(t.c.is_active.desc(), t.c.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        return list(await self._session.scalars(stmt))

    async def count(self, filters: UserFilter) -> int:
        stmt = sa.select(sa.func.count()).select_from(t).where(*self._conditions(filters))
        return (await self._session.scalar(stmt)) or 0

    @staticmethod
    def _conditions(f: UserFilter) -> list[sa.ColumnElement[Any]]:
        conditions: list[sa.ColumnElement[Any]] = []
        if f.email:
            conditions.append(t.c.email.ilike(f"%{f.email}%"))
        if f.full_name:
            conditions.append(t.c.full_name.ilike(f"%{f.full_name}%"))
        if f.role is not None:
            conditions.append(t.c.role == f.role)
        if f.is_active is not None:
            conditions.append(t.c.is_active.is_(f.is_active))
        if f.created_from is not None:
            conditions.append(t.c.created_at >= f.created_from)
        if f.created_to is not None:
            conditions.append(t.c.created_at <= f.created_to)
        return conditions
