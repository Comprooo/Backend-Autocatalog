from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Optional

class Car(Document):
    brand: str
    model: str
    year: int
    price: float
    condition: str = ""
    transmission: str # e.g., Automatic, Manual
    mileage: int
    fuel: str # e.g., Bensin, Diesel, Listrik
    color: str
    car_type: str = "MPV" # e.g., MPV, SUV, Sedan
    description: str
    status: str = "Tersedia" # "Tersedia", "Terjual"
    sold_at: Optional[datetime] = None
    features: List[str] = []
    images: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "cars"
