from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
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
