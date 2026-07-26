from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, update

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import User
from app.infrastructure.repositories import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(selectinload(User.roles)).where(User.email == email)  # noqa
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_id(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if user:
            await self.session.refresh(user, ["roles"])

        return user

    async def update(self, user_id: UUID, data: dict) -> User | None:
        data["updatedAt"] = datetime.now(timezone.utc)
        stmt = update(User).where(User.id == user_id).values(**data).returning(User)    # noqa

        try:
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_paginated(self, offset: int, limit: int) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles))  # noqa
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
