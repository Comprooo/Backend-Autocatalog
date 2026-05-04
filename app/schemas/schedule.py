from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, Any
from datetime import datetime, date, time
from app.schemas.car import CarResponse

class ScheduleCreate(BaseModel):
    car_id: str
    schedule_date: date # YYYY-MM-DD
    time: str # HH:MM
    phone: str = Field(pattern=r'^[0-9]+$', description="Phone number must contain only digits", examples=["081234567890"])
    notes: Optional[str] = None

class ScheduleStatusUpdate(BaseModel):
    status: str

class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    user_id: Any
    car_id: Any
    date: datetime
    phone: str
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "user_id", "car_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        return str(v)

class ScheduleDetailResponse(ScheduleResponse):
    car: Optional[CarResponse] = None
