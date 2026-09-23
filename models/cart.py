from datetime import datetime
from typing import List, Dict, Any
from beanie import Document
from pydantic import BaseModel, Field

class CartItem(BaseModel):
    product_id: str
    quantity: int

class Cart(Document):
    user_id: str
    items: List[Dict[str, Any]] = [] # list of {"product_id": str, "quantity": int}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "carts"
        indexes = [
            "user_id"
        ]
