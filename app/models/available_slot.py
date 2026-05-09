from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime, timezone, date

class AvailableSlot(Document):
    location_id: PydanticObjectId
    date: date
    time_start: str # HH:MM
    time_end: str   # HH:MM
    quota: int = 1
    booked_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_available(self) -> bool:
        return self.booked_count < self.quota

    class Settings:
        name = "available_slots"
