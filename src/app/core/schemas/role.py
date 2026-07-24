from enum import Enum
from uuid import UUID

from app.core.schemas.base import PyModel


class RoleCode(str, Enum):
    VIEW = "VIEW"
    APPR = "APPR"
    EXPR = "EXPR"
    ADMN = "ADMN"


class RoleRead(PyModel):
    id: UUID
    code: RoleCode
    value: str
    description: str | None = None
