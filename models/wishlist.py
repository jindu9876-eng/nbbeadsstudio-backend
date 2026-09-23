from datetime import datetime
from typing import List
from beanie import Document
from pydantic import Field

class Wishlist(Document):
    user_id: str
    product_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "wishlists"
        indexes = [
            "user_id"
        ]
