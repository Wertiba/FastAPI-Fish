from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas.base import DatetimeResponse, PyModel


class FlagType(str, Enum):
    STRING = "STRING"
    BOOL = "BOOL"
    NUMBER = "NUMBER"


class FlagCreateBody(PyModel):
    code: Annotated[str, Field(max_length=100)]
    default: Annotated[str, Field(max_length=255)]
    type: FlagType


class FlagReadResponse(FlagCreateBody, DatetimeResponse):
    id: UUID
    createdAt: datetime
    updatedAt: datetime


class FlagUpdateBody(PyModel):
    default: Annotated[str, Field(max_length=255)]
    updatedAt: datetime | None = None
