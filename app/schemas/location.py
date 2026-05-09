from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any
from datetime import datetime

class LocationBase(BaseModel):
    location_name: str
    address: str
    map_link: str

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: Any
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)
