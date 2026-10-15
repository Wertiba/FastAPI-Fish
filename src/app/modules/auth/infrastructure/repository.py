from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.ports import RefreshTokenRepository
from app.modules.auth.domain.entities import RefreshToken
from app.modules.auth.infrastructure.tables import refresh_tokens_table as t


class SqlRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(token)
        await self._session.flush()

    async def get(self, user_id: UUID, token_hash: str) -> RefreshToken | None:
        stmt = sa.select(RefreshToken).where(t.c.user_id == user_id, t.c.token_hash == token_hash)
        return (await self._session.scalars(stmt)).one_or_none()

    async def delete_by_hash(self, token_hash: str) -> None:
        await self._session.execute(sa.delete(t).where(t.c.token_hash == token_hash))

    async def delete_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(sa.delete(t).where(t.c.user_id == user_id))
