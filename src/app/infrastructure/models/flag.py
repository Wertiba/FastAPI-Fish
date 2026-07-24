import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from app.core.schemas.flag import FlagType

if TYPE_CHECKING:
    from app.infrastructure.models import User
    from app.infrastructure.models.experiment import Experiment


class Flag(SQLModel, table=True):
    __tablename__ = "flags"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, nullable=False, index=True, max_length=100)
    default: str = Field(nullable=False)
    type: FlagType = Field(nullable=False)

    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    createdBy: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    creator: "User" = Relationship(back_populates="created_flags")

    flag_experiments: list["Experiment"] = Relationship(back_populates="flag")
