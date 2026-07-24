import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.infrastructure.models import User
    from app.infrastructure.models.event import Event
    from app.infrastructure.models.experiment import Variant


class Decision(SQLModel, table=True):
    __tablename__ = "decisions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    variant_id: uuid.UUID = Field(foreign_key="variants.id", nullable=False)
    isRequested: bool = Field(default=False, nullable=False)

    user: "User" = Relationship(back_populates="decisions")
    variant: "Variant" = Relationship(back_populates="decisions")

    events: list["Event"] = Relationship(back_populates="decision")

    __table_args__ = (
        UniqueConstraint('user_id', 'variant_id', name='uq_user_variant'),
    )
