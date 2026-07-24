import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from app.core.schemas.role import RoleCode

if TYPE_CHECKING:
    from app.infrastructure.models.decision import Decision
    from app.infrastructure.models.event import EventCatalog
    from app.infrastructure.models.experiment import Experiment
    from app.infrastructure.models.flag import Flag
    from app.infrastructure.models.metric import Metric, MetricCatalog
    from app.infrastructure.models.review import Approver


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True, index=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", primary_key=True)


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    code: RoleCode = Field(nullable=False, unique=True)
    value: str = Field(nullable=False)
    description: str = Field(nullable=True)

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRole)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, nullable=False)
    password: str = Field(nullable=False)
    fullName: str = Field(nullable=False)
    exp_index: int = Field(nullable=False, default=100, le=100, ge=0)
    isActive: bool = Field(default=True)

    required: int | None = Field(nullable=False, default=0, ge=0)

    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    roles: list["Role"] = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"lazy": "selectin"},
        link_model=UserRole,
    )
    created_catalog_metrics: list["MetricCatalog"] = Relationship(back_populates="creator")
    created_flags: list["Flag"] = Relationship(back_populates="creator")
    created_experiments: list["Experiment"] = Relationship(back_populates="creator")
    decisions: list["Decision"] = Relationship(back_populates="user")
    created_catalog_events: list["EventCatalog"] = Relationship(back_populates="creator")

    approvers_as_experimenter: list["Approver"] = Relationship(
        back_populates="experimenter",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.experimenter_id"
        }
    )
    approvers_as_approver: list["Approver"] = Relationship(
        back_populates="approver",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.approver_id"
        }
    )
    approvers_as_creator: list["Approver"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={
            "foreign_keys": "Approver.addedBy"
        }
    )
