"""Scheduled jobs of ``auth``; scheduled in ``auth/module.py``."""

from dataclasses import dataclass

from app.modules.auth.application.ports import RefreshTokenGateway
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.domain.time import TimeService


@dataclass
class CleanupExpiredRefreshTokens:
    """Expired refresh tokens are useless; without this job the table only grows."""

    uow: UnitOfWork
    refresh_token_gateway: RefreshTokenGateway
    time: TimeService

    async def __call__(self) -> None:
        await self.refresh_token_gateway.delete_expired(self.time.now())
        await self.uow.commit()
