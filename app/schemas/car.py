from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Any
from datetime import datetime

class CarSpecifications(BaseModel):
    year: int
    transmission: str
    color: str
    mileage: str # "45000 km"
    fuel: str
    type: str # MPV, SUV, etc

class CarCreate(BaseModel):
    brand: str
    model: str
    price: float = Field(gt=0)
    condition: str
    specifications: CarSpecifications
    images: List[str] = []
    features: List[str] = []
    description: str = ""

class CarUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    price: Optional[float] = None
    condition: Optional[str] = None
    specifications: Optional[CarSpecifications] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None
    description: Optional[str] = None
    status: Optional[str] = None

class CarStatusUpdate(BaseModel):
    status: str

class CarListResponse(BaseModel):
    car_id: str
    brand: str
    model: str
    price: float
    condition: str
    thumbnail_url: str

class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    car_id: str
    brand: str
    model: str
    price: float
    status: str
    condition: str
    specifications: CarSpecifications
    features: List[str]
    description: str
    images: List[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("car_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

    @classmethod
    def from_model(cls, c: Any):
        return cls(
            car_id=str(c.id),
            brand=c.brand,
            model=c.model,
            price=c.price,
            status=c.status,
            condition=c.condition,
            specifications=CarSpecifications(
                year=c.year,
                transmission=c.transmission,
                color=c.color,
                mileage=f"{c.mileage:,} km".replace(",", "."),
                fuel=c.fuel,
                type=c.car_type
            ),
            features=c.features,
            description=c.description,
            images=c.images,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
