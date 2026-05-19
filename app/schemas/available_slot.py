from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Optional
from datetime import datetime, date
from app.schemas.location import LocationResponse

class AvailableSlotBase(BaseModel):
    location_id: str
    date: date
    time_start: str # HH:MM
    time_end: str   # HH:MM
    quota: int = 1

class AvailableSlotCreate(AvailableSlotBase):
    pass

class AvailableSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slot_id: Any
    location: Optional[LocationResponse] = None
    date: date
    time: str # "HH:MM - HH:MM"
    is_available: bool

    @field_validator("slot_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

    @classmethod
    def from_model(cls, model: Any, location: Optional[Any] = None):
        return cls(
            slot_id=str(model.id),
            location=LocationResponse.model_validate(location) if location else None,
            date=model.date,
            time=f"{model.time_start} - {model.time_end}",
            is_available=model.booked_count < model.quota
        )

class AdminAvailableSlotResponse(AvailableSlotBase):
    model_config = ConfigDict(from_attributes=True)
    id: Any
    booked_count: int
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "location_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

class AvailableSlotUpdate(BaseModel):
    location_id: Optional[str] = None
    date: Optional[date] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    quota: Optional[int] = None
