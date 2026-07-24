from datetime import datetime, timezone
from uuid import UUID

from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, select

from app.core.exceptions.base import DuplicateError, RelationNotFoundError, RepositoryError
from app.infrastructure.models import Decision, Event, EventCatalog, Variant
from app.infrastructure.repositories import BaseRepository


class EventRepository(BaseRepository[EventCatalog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=EventCatalog)

    async def get_by_code(self, code: str) -> EventCatalog:
        try:
            stmt = select(EventCatalog).where(and_(EventCatalog.code == code, EventCatalog.inArchive == False))  # noqa
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def assign_event(self, event: Event) -> Event:
        try:
            self.session.add(event)
            await self.session.flush()
            await self.session.refresh(event)
            return event
        except IntegrityError as e:
            orig = e.orig
            pgcode = getattr(orig, 'pgcode', None)

            if pgcode == ForeignKeyViolationError.sqlstate:
                raise RelationNotFoundError("Referenced entity does not exist") from e
            elif pgcode == UniqueViolationError.sqlstate:
                raise DuplicateError("Unique field already exists") from e
            raise
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_experiment_and_event_codes(
            self, experiment_id: UUID, event_codes: list[str], time_from: datetime
    ) -> list[Event]:
        if time_from.tzinfo is not None:
            time_from = time_from.astimezone(timezone.utc).replace(tzinfo=None)

        stmt = (
            select(Event)
            .join(Event.decision)
            .join(Decision.variant)
            .where(
                Variant.experiment_id == experiment_id,
                Event.eventCatalog_code.in_(event_codes),
                Event.createdAt >= time_from,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_variant_and_event_codes(
            self,
            variant_id: UUID,
            event_codes: list[str],
            time_from: datetime,
            time_to: datetime,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .join(Event.decision)
            .where(and_(
                Decision.variant_id == variant_id,
                Event.eventCatalog_code.in_(event_codes),
                Event.createdAt >= time_from,
                Event.createdAt < time_to,
            ))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_exposure(self, decision_id: UUID, type: str = "EXPOSURE") -> list[Event] or None:
        stmt = select(Event).where(and_(
            Event.decision_id == decision_id,   # noqa
            Event.eventCatalog_code == type,    # noqa
        ))
        result = await self.session.execute(stmt)
        return None or list(result.scalars().all())
