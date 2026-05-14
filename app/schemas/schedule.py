from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, Any, List
from datetime import datetime, date, time
from app.schemas.car import CarResponse

class ScheduleCreate(BaseModel):
    car_id: str
    slot_id: str
    email: str
    phone: str
    notes: Optional[str] = None

class ScheduleStatusUpdate(BaseModel):
    status: str

class ScheduleReschedule(BaseModel):
    new_slot_id: str
    notes: Optional[str] = None

class AppointmentSummary(BaseModel):
    total: int
    pending: int
    confirmed: int
    cancelled: int
    completed: int

class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    user_id: Any
    car_id: Any
    slot_id: Any
    email: str
    phone: str
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "user_id", "car_id", "slot_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

class ScheduleDetailResponse(ScheduleResponse):
    car: Optional[CarResponse] = None
    slot: Optional[Any] = None # Will be AvailableSlotResponse

class MyAppointmentsResponse(BaseModel):
    summary: AppointmentSummary
    appointments: List[ScheduleDetailResponse]
