from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.core.utils import TimeHelper


class PyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DatetimeResponse(PyModel):
    @field_serializer("createdAt", "updatedAt", check_fields=False)
    def serialize_dt(self, dt: datetime, _info) -> str:
        return TimeHelper.to_iso_z(dt)
