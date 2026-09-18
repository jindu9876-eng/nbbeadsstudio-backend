from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field

# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "user"
    username: str

# Product schemas
class ProductCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: str
    short_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    mrp: float = Field(..., ge=0)
    sale_price: float = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    sku: str
    tags: List[str] = []
    color: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[str] = None
    dimensions: Optional[str] = None
    featured: bool = False
    trending: bool = False
    best_seller: bool = False
    status: str = "active"
    thumbnail: Optional[str] = None
    gallery_images: List[str] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    mrp: Optional[float] = Field(None, ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[str] = None
    dimensions: Optional[str] = None
    featured: Optional[bool] = None
    trending: Optional[bool] = None
    best_seller: Optional[bool] = None
    status: Optional[str] = None
    thumbnail: Optional[str] = None
    gallery_images: Optional[List[str]] = None

# Category schemas
class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    status: str = "active"

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None

# Cart item schemas
class CartItemUpdate(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

# Wishlist schemas
class WishlistUpdate(BaseModel):
    product_id: str

# Order schemas
class ShippingAddressSchema(BaseModel):
    name: str
    address: str
    city: str
    postal_code: str
    phone: str

class OrderCreate(BaseModel):
    items: List[Dict[str, Any]] # [{"product_id": str, "quantity": int}]
    shipping_address: ShippingAddressSchema
    coupon_code: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    shipping_status: str # "pending", "packed", "shipped", "delivered", "cancelled"
    payment_status: Optional[str] = None # "pending", "paid", "failed"

# Banner schemas
class BannerCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    image: str
    sort_order: int = 0
    status: str = "active"

class BannerUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    image: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None
