from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Any
from datetime import datetime

class CarCreate(BaseModel):
    brand: str
    type: str
    year: int
    price: float = Field(gt=0, description="Price must be greater than 0")
    transmission: str
    mileage: int
    fuel: str
    color: str
    description: str
    status: str = "Tersedia"
    features: List[str] = []
    images: List[str] = []

class CarUpdate(BaseModel):
    brand: Optional[str] = None
    type: Optional[str] = None
    year: Optional[int] = None
    price: Optional[float] = Field(None, gt=0)
    transmission: Optional[str] = None
    mileage: Optional[int] = None
    fuel: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None

class CarStatusUpdate(BaseModel):
    status: str

class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    brand: str
    type: str
    year: int
    price: float
    transmission: str
    mileage: int
    fuel: str
    color: str
    description: str
    status: str
    features: List[str]
    images: List[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)
