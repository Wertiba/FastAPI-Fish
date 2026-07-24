import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.schemas.experiment import ExperimentStatus

if TYPE_CHECKING:
    from app.infrastructure.models import Flag, Metric, User
    from app.infrastructure.models.decision import Decision
    from app.infrastructure.models.review import Review


class Experiment(SQLModel, table=True):
    __tablename__ = "experiments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(nullable=False, index=True, max_length=100)
    flag_code: str = Field(foreign_key="flags.code", nullable=False)

    name: str = Field(nullable=False, max_length=255)
    status: ExperimentStatus = Field(nullable=False, max_length=255, default=ExperimentStatus.DRAFT)
    version: float = Field(nullable=False, default=1.0, ge=0)
    part: int = Field(nullable=False, default=0, le=100, ge=0)
    target: str | None = Field(nullable=True, max_length=500)
    isCurrent: bool = Field(nullable=False, default=True)
    description: str = Field(nullable=False, max_length=255)
    resultVariant_id: uuid.UUID | None = Field(nullable=True, default=None)
    comment: str | None = Field(nullable=True, max_length=255, default=None)

    createdBy: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    createdAt: datetime = Field(default_factory=datetime.now)

    creator: "User" = Relationship(back_populates="created_experiments")
    flag: "Flag" = Relationship(back_populates="flag_experiments")

    metrics: list["Metric"] = Relationship(back_populates="experiment")
    variants: list["Variant"] = Relationship(back_populates="experiment")
    reviews: list["Review"] = Relationship(back_populates="experiment")

    __table_args__ = (
        UniqueConstraint('code', 'version', name='uq_code_version'),
    )


class Variant(SQLModel, table=True):
    __tablename__ = "variants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    experiment_id: uuid.UUID = Field(foreign_key="experiments.id", nullable=False)
    name: str = Field(nullable=False, max_length=255)
    value: str = Field(nullable=False, max_length=255)
    weight: int = Field(nullable=False, default=0, ge=0)
    isControl: bool = Field(nullable=False, default=True)

    experiment: "Experiment" = Relationship(back_populates="variants")

    decisions: list["Decision"] = Relationship(back_populates="variant")
