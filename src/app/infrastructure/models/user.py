import uuid
from datetime import datetime, timezone

from pydantic import EmailStr, model_validator
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from app.core.schemas.user import UserRole


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, nullable=False)
    password: str = Field(nullable=False)
    fullName: str = Field(nullable=False)
    isActive: bool = Field(default=True)
    roles: list[UserRole] = Field(default=[UserRole.USER])
    createdBy: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)

    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    creator: "User | None" = Relationship(
        sa_relationship_kwargs={"remote_side": "User.id"},
    )

    @model_validator(mode="after")
    def default_created_by_to_self(self) -> "User":
        if self.createdBy is None:
            self.createdBy = self.id
        return self
