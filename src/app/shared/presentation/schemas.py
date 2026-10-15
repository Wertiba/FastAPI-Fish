"""Базовые Pydantic-схемы HTTP-слоя: camelCase снаружи, snake_case внутри."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from app.shared.application.pagination import Page as PageResult
from app.shared.domain.time import as_aware_utc, utc_now

T = TypeVar("T")
S = TypeVar("S")


def format_utc(value: datetime) -> str:
    """``2026-01-02T03:04:05.678Z``"""
    return as_aware_utc(value).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timestamp_now() -> str:
    """``2026-01-02T03:04:05Z`` — метка времени для тел ошибок."""
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(format_utc, return_type=str, when_used="json")]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


# Имя ``Page`` даёт в OpenAPI компоненту ``Page_UserReadResponse_``, как в Fish.
class Page(CamelModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int

    @classmethod
    def from_page(cls, page: PageResult[S], convert: Callable[[S], T]) -> Self:
        return cls(
            items=[convert(item) for item in page.items],
            page=page.page,
            size=page.size,
            total=page.total,
        )


class PingResponse(CamelModel):
    status: str = "ok"


class ErrorResponse(CamelModel):
    code: str
    message: str
    trace_id: str
    timestamp: str
    path: str
    details: dict[str, Any] | None = None


class FieldError(CamelModel):
    field: str
    issue: str
    rejected_value: Any = None


class ValidationErrorResponse(CamelModel):
    code: str = "VALIDATION_FAILED"
    message: str = "Some fields are not correct."
    trace_id: str
    timestamp: str
    path: str
    field_errors: list[FieldError]
