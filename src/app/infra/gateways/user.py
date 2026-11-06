from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import ApplicationError
from app.application.ports.user_gateway import UserCriteria, UserGateway
from app.domain.users.entity import User


class SqlAlchemyUserGateway(UserGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: UUID) -> User | None:
        try:
            return await self.session.get(User, id_)
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def get_all(self, offset: int, limit: int, criteria: UserCriteria) -> list[User]:
        stmt = self._apply_criteria(select(User), criteria)
        stmt = stmt.order_by(User.is_active.desc(), User.created_at.desc(), User.id)
        stmt = stmt.offset(offset).limit(limit)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def count(self, criteria: UserCriteria) -> int:
        stmt = self._apply_criteria(select(func.count()).select_from(User), criteria)
        try:
            result = await self.session.execute(stmt)
            return int(result.scalar_one())
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    @staticmethod
    def _apply_criteria[S: Select[Any]](stmt: S, criteria: UserCriteria) -> S:
        conditions: list[ColumnElement[bool]] = []
        if criteria.email:
            conditions.append(User.email.icontains(criteria.email, autoescape=True))
        if criteria.full_name:
            conditions.append(User.full_name.icontains(criteria.full_name, autoescape=True))
        if criteria.role is not None:
            conditions.append(User.role == criteria.role)
        if criteria.is_active is not None:
            conditions.append(User.is_active.is_(criteria.is_active))
        if criteria.created_from is not None:
            conditions.append(User.created_at >= criteria.created_from)
        if criteria.created_to is not None:
            conditions.append(User.created_at <= criteria.created_to)
        return stmt.where(*conditions)
