"""Every entity, imported so their tables land in ``metadata``: Alembic autogenerate and tests read it."""

from app.domain.base import Base
from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.entity import User

__all__ = ["RefreshToken", "User", "metadata"]

metadata = Base.metadata
