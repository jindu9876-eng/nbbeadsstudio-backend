from datetime import datetime
from typing import Optional
from backend.pg_engine import Document
from pydantic import Field, EmailStr

class User(Document):
    name: str
    email: EmailStr
    password_hash: str
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "active" # "active", "blocked"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            "email",
            "status"
        ]
