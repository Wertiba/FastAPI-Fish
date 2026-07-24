from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.infrastructure.models import Role
from app.infrastructure.repositories import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Role)

    async def get_by_codes(self, codes: list[str]) -> list[Role]:
        statement = select(Role).where(Role.code.in_(codes))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Role | None:
        statement = select(Role).where(Role.code == code)
        result = await self.session.execute(statement)
        return result.first()
