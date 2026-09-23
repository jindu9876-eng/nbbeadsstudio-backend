from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import Field

class Product(Document):
    name: str
    slug: str
    description: str
    short_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    mrp: float
    sale_price: float
    discount_percent: Optional[float] = None
    stock: int
    sku: str
    tags: List[str] = []
    color: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[str] = None
    dimensions: Optional[str] = None
    featured: bool = False
    trending: bool = False
    best_seller: bool = False
    status: str = "active" # "active", "inactive", or "archived"
    thumbnail: Optional[str] = None
    gallery_images: List[str] = []
    variants: List[dict] = [] # list of {"sku": str, "title": str, "price": float, "stock": int, "attributes": dict, "image": Optional[str]}
    seo: Optional[dict] = None # {"meta_title": str, "meta_description": str, "meta_keywords": List[str], "canonical_url": Optional[str]}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "products"
        indexes = [
            "slug",
            "sku",
            "category",
            "status",
            "featured",
            "trending",
            "best_seller"
        ]
        
    def calculate_discount(self):
        if self.mrp > 0:
            self.discount_percent = round(((self.mrp - self.sale_price) / self.mrp) * 100, 2)
        else:
            self.discount_percent = 0.0
