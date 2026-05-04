from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional
from app.models.user import User
from app.models.car import Car

class Schedule(Document):
    user_id: PydanticObjectId
    car_id: PydanticObjectId
    date: datetime # Combined schedule_date and time
    phone: str = "" # Default to empty for existing records
    notes: Optional[str] = None
    status: str = "pending" # "pending", "confirmed", "cancelled", "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "schedules"
