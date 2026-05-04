from beanie import Document, Indexed
from pydantic import Field, EmailStr
from datetime import datetime, timezone
from typing import Optional

class User(Document):
    username: Indexed(str, unique=True)
    email: Indexed(EmailStr, unique=True)
    phone: str = ""
    hashed_password: str
    role: str = "customer" # "customer", "admin", "internal_ai_service"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
