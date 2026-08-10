from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import RefreshToken
from app.infrastructure.repositories.base_repo import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=RefreshToken)

    async def get_by_user_and_hash(self, user_id: UUID, hashed_token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.hashed_token == hashed_token,
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def delete_by_hash(self, hashed_token: str) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def delete_all_for_user(self, user_id: UUID) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
