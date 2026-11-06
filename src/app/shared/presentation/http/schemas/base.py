from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, field_validator

from app.shared.domain.time import TimeService, utc_now


def format_utc(value: datetime) -> str:
    """``2026-01-02T03:04:05.678Z``"""
    return TimeService.to_iso(value)


def timestamp_now() -> str:
    """``2026-01-02T03:04:05Z``: timestamp of an error body."""
    return TimeService.to_iso(utc_now(), timespec="seconds")


UtcDatetime = Annotated[datetime, PlainSerializer(format_utc, return_type=str, when_used="json")]


class PyModel(BaseModel):
    """Field names are the camelCase names of the API, so schemas need no aliases."""

    model_config = ConfigDict(from_attributes=True, allow_inf_nan=False)

    @field_validator("*")
    @classmethod
    def reject_nul(cls, value: object) -> object:
        # Postgres text cannot hold NUL, so such input would fail in the database with a 500.
        texts = value if isinstance(value, list) else [value]
        if any(isinstance(text, str) and "\x00" in text for text in texts):
            raise ValueError("text must not contain NUL characters")
        return value
