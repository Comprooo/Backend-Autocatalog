from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Optional

class Car(Document):
    brand: str
    type: str
    year: int
    price: float
    transmission: str # e.g., Automatic, Manual
    mileage: int
    fuel: str # e.g., Bensin, Diesel, Listrik
    color: str
    description: str
    status: str = "Tersedia" # "Tersedia", "Terjual"
    features: List[str] = []
    images: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "cars"
