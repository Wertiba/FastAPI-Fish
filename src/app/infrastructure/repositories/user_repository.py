from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
from app.core.schemas.user import UserFilterQuery
from app.infrastructure.models import User
from app.infrastructure.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def update(self, user_id: UUID, data: dict[str, Any]) -> User | None:
        data["updated_at"] = datetime.now(UTC)
        return await super().update(user_id, data)

    async def get_filtered(self, filters: UserFilterQuery, offset: int, limit: int) -> list[User]:
        stmt = self._apply_filters(select(User), filters)
        stmt = stmt.order_by(User.is_active.desc(), User.created_at.desc()).offset(offset).limit(limit)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def count_filtered(self, filters: UserFilterQuery) -> int:
        stmt = self._apply_filters(select(func.count()).select_from(User), filters)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    @staticmethod
    def _apply_filters(stmt: Select, filters: UserFilterQuery) -> Select:
        if filters.email:
            stmt = stmt.where(User.email.ilike(f"%{filters.email}%"))
        if filters.fullName:
            stmt = stmt.where(User.full_name.ilike(f"%{filters.fullName}%"))
        if filters.role is not None:
            stmt = stmt.where(User.role == filters.role)
        if filters.isActive is not None:
            stmt = stmt.where(User.is_active == filters.isActive)
        if filters.createdFrom is not None:
            stmt = stmt.where(User.created_at >= filters.createdFrom)
        if filters.createdTo is not None:
            stmt = stmt.where(User.created_at <= filters.createdTo)
        return stmt
