from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class PyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DatetimeResponse(PyModel):
    @field_serializer("createdAt", "updatedAt", check_fields=False)
    def serialize_dt(self, dt: datetime, _info) -> str:
        utc_dt = dt.astimezone(timezone.utc)
        iso_str = utc_dt.isoformat()
        if iso_str.endswith("+00:00"):
            return iso_str[:-9] + "Z"
        return iso_str[:-3] + "Z"
