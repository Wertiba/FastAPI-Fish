import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.schemas.review import ReviewResult

if TYPE_CHECKING:
    from app.infrastructure.models import Experiment, User


class Approver(SQLModel, table=True):
    __tablename__ = "approvers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    experimenter_id: uuid.UUID = Field(foreign_key="users.id")
    approver_id: uuid.UUID = Field(foreign_key="users.id")
    isActive: bool = Field(default=True, nullable=False)
    addedAt: datetime = Field(default_factory=datetime.now)
    addedBy: uuid.UUID = Field(foreign_key="users.id")

    experimenter: "User" = Relationship(
        back_populates="approvers_as_experimenter",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.experimenter_id"
        }
    )
    approver: "User" = Relationship(
        back_populates="approvers_as_approver",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.approver_id"
        }
    )
    creator: "User" = Relationship(
        back_populates="approvers_as_creator",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.addedBy"
        }
    )

    reviews: list["Review"] = Relationship(back_populates="approver")


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    experiment_id: uuid.UUID = Field(foreign_key="experiments.id")
    result: ReviewResult = Field(nullable=False)
    comment: str = Field(nullable=True, max_length=500)

    createdAt: datetime = Field(default_factory=datetime.now)
    approvedBy: uuid.UUID = Field(foreign_key="approvers.id")

    experiment: "Experiment" = Relationship(back_populates="reviews")
    approver: "Approver" = Relationship(back_populates="reviews")

    __table_args__ = (
        UniqueConstraint('experiment_id', 'approvedBy', name='uq_experiment_id_approvedBy'),
    )
