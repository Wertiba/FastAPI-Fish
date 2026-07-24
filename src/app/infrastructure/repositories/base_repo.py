from datetime import datetime, timezone
from typing import Generic
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.custom_types import T
from app.core.exceptions.base import DuplicateError, RepositoryError
from app.core.schemas.base import PyModel


class BaseRepository(Generic[T]):  # noqa
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def add(self, obj: T) -> T:
        try:
            self.session.add(obj)
            await self.session.flush()
            await self.session.refresh(obj)
            return obj
        except IntegrityError as e:
            raise DuplicateError("Unique field already exists") from e
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def deactivate(self, id_: UUID, **values) -> None:
        stmt = update(self.model).where(self.model.id == id_).values(**values)  # noqa
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def update(self, id_: UUID, new_data: PyModel) -> T | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id_)    # noqa
            .values(**new_data.model_dump(exclude_unset=True))
            .returning(self.model)
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_id(self, id_: UUID) -> T | None:
        try:
            stmt = select(self.model).where(self.model.id == id_)  # type: ignore[attr-defined]
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_all(self) -> list[T]:
        try:
            res = await self.session.execute(select(self.model))
            return list(res.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_paginated(self, offset: int, limit: int) -> list[T]:
        try:
            q = select(self.model).offset(offset).limit(limit)
            result = await self.session.execute(q)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def count(self) -> int:
        q = select(func.count()).select_from(self.model)
        result = await self.session.execute(q)
        return result.scalar_one()
