from typing import Any

from app.shared.domain.time import utc_now


def apply_changes[T](entity: T, changes: dict[str, Any]) -> T:
    for name, value in changes.items():
        setattr(entity, name, value)
    if hasattr(entity, "updated_at"):
        entity.updated_at = utc_now()
    return entity
