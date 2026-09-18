from datetime import datetime
from backend.pg_engine import Document
from pydantic import Field, EmailStr

class Admin(Document):
    username: str
    email: EmailStr
    password_hash: str
    status: str = "active" # "active", "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "admins"
        indexes = [
            "username",
            "email",
            "status"
        ]
