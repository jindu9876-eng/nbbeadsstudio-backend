from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field

class Category(Document):
    name: str
    slug: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    status: str = "active" # "active" or "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"
        indexes = [
            "slug",
            "status"
        ]
