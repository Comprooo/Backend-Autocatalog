from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from datetime import datetime
from typing import Optional, Any

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    phone: str = Field(pattern=r'^[0-9]+$', description="Phone number must contain only digits", examples=["081234567890"])
    password: str
    password_confirm: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Any
    username: str
    email: EmailStr
    phone: str
    role: str
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "customer"
