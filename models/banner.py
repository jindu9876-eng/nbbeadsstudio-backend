from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field

class Banner(Document):
    title: str
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    image: str
    sort_order: int = 0
    status: str = "active" # "active", "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "banners"
        indexes = [
            "status",
            "sort_order"
        ]
