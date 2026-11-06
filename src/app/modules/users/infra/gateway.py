from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.application.ports import UserCriteria, UserGateway
from app.modules.users.domain.entity import User
from app.modules.users.infra.tables import users
from app.shared.application.exceptions import ApplicationError
from app.shared.domain.ids import UserId


class SqlAlchemyUserGateway(UserGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: UserId) -> User | None:
        try:
            return await self.session.get(User, id_)
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(users.c.email == email)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def get_all(self, offset: int, limit: int, criteria: UserCriteria) -> list[User]:
        stmt = self._apply_criteria(select(User), criteria)
        stmt = stmt.order_by(users.c.is_active.desc(), users.c.created_at.desc(), users.c.id)
        stmt = stmt.offset(offset).limit(limit)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def count(self, criteria: UserCriteria) -> int:
        stmt = self._apply_criteria(select(func.count()).select_from(users), criteria)
        try:
            result = await self.session.execute(stmt)
            return int(result.scalar_one())
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    @staticmethod
    def _apply_criteria[S: Select[Any]](stmt: S, criteria: UserCriteria) -> S:
        conditions: list[ColumnElement[bool]] = []
        if criteria.email:
            conditions.append(users.c.email.icontains(criteria.email, autoescape=True))
        if criteria.full_name:
            conditions.append(users.c.full_name.icontains(criteria.full_name, autoescape=True))
        if criteria.role is not None:
            conditions.append(users.c.role == criteria.role)
        if criteria.is_active is not None:
            conditions.append(users.c.is_active.is_(criteria.is_active))
        if criteria.created_from is not None:
            conditions.append(users.c.created_at >= criteria.created_from)
        if criteria.created_to is not None:
            conditions.append(users.c.created_at <= criteria.created_to)
        return stmt.where(*conditions)
