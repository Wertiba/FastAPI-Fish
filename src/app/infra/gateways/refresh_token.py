from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import ApplicationError
from app.application.ports.refresh_token_gateway import RefreshTokenGateway
from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.ids import UserId
from app.infra.database.mappings import refresh_tokens


class SqlAlchemyRefreshTokenGateway(RefreshTokenGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_and_hash(self, user_id: UserId, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            refresh_tokens.c.user_id == user_id, refresh_tokens.c.token_hash == token_hash
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(refresh_tokens.c.token_hash == token_hash)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def delete_by_user(self, user_id: UserId) -> None:
        try:
            await self.session.execute(delete(refresh_tokens).where(refresh_tokens.c.user_id == user_id))
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc
