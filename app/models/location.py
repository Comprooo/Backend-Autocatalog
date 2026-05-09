from beanie import Document
from pydantic import Field
from datetime import datetime, timezone

class Location(Document):
    location_name: str
    address: str
    map_link: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "locations"
