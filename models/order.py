from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document
from pydantic import Field

class Order(Document):
    user_id: Optional[str] = None
    items: List[Dict[str, Any]] = [] # list of {"product_id": str, "name": str, "price": float, "quantity": int, "image": str}
    subtotal: float
    shipping: float
    gst: float
    discount: float = 0.0
    total: float
    payment_status: str = "pending" # "pending", "paid", "failed"
    shipping_status: str = "pending" # "pending", "packed", "shipped", "delivered", "cancelled"
    shipping_address: Dict[str, Any] = {} # {"name": str, "address": str, "city": str, "postal_code": str, "phone": str}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "orders"
        indexes = [
            "user_id",
            "shipping_status",
            "payment_status",
            "created_at"
        ]
