from typing import Annotated, AnyStr
from uuid import UUID

from pydantic import Field

from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.experiment import VariantData


class SubjectAttributes(PyModel):
    country: Annotated[str | None, Field(max_length=255)] = None
    app_version: Annotated[str | None, Field(max_length=255)] = None
    platform: Annotated[str | None, Field(max_length=255)] = None
    screen: Annotated[str | None, Field(max_length=255)] = None


class DecisionBody(PyModel):
    user_id: UUID
    attributes: SubjectAttributes
    flag_codes: list[str]


class DecisionData(DatetimeResponse):
    user_id: UUID
    flag_code: str
    value: AnyStr
    experiment_code: str | None = None
    variant: VariantData | None = None
    decision_id: UUID | None = None


class DecisionResponse(PyModel):
    items: list[DecisionData]
