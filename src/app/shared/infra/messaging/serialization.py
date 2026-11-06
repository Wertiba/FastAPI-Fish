"""Event <-> JSON. The payload is the dataclass fields; consumers validate it against their own class."""

import dataclasses
import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from app.shared.application.events import IntegrationEvent


def _default(value: object) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Cannot serialize {type(value).__name__} in an event payload")


def to_payload(event: IntegrationEvent) -> str:
    return json.dumps(dataclasses.asdict(event), default=_default, ensure_ascii=False, separators=(",", ":"))


def from_payload[E: IntegrationEvent](event_cls: type[E], payload: str | bytes) -> E:
    return TypeAdapter(event_cls).validate_json(payload)
