from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base, str_enum, utc_now
from app.domain.users.enums import UserRole


class User(Base, kw_only=True):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(server_default=true(), default=True)
    # Required in the table; a self-registered user is its own creator, set right after construction.
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=False, default=None)
    created_at: Mapped[datetime] = mapped_column(default_factory=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default_factory=utc_now)
