import os
import io
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Response
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field

from backend.models.product import Product
from backend.models.category import Category
from backend.models.user import User
from backend.models.order import Order
from backend.models.wishlist import Wishlist
from backend.models.cart import Cart
from backend.models.admin import Admin
from backend.utils.security import verify_password, get_password_hash, create_access_token
from backend.routes.dependencies import get_current_admin
from backend.utils.response import api_response
from backend.utils.cloudinary_service import upload_image_file, upload_image_from_url, is_cloudinary_configured
from backend.utils.bulk_import import (
    generate_csv_template,
    generate_excel_template,
    validate_bulk_file,
    execute_bulk_import
)

router = APIRouter(prefix="/admin", tags=["Admin API"])

# --- Models & Request Schemas ---

class AdminLoginPayload(BaseModel):
    username: str
    password: str

class ProductAdminCreate(BaseModel):
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
    status: str = "active" # active, inactive, archived
    thumbnail: Optional[str] = None
    gallery_images: List[str] = []
    variants: List[Dict[str, Any]] = []
    seo: Optional[Dict[str, Any]] = None

class ProductAdminUpdate(BaseModel):
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
    variants: Optional[List[Dict[str, Any]]] = None
    seo: Optional[Dict[str, Any]] = None

class ProductStockUpdate(BaseModel):
    stock: int = Field(..., ge=0)

class ProductStatusUpdate(BaseModel):
    status: str # active, inactive, archived

class BulkActionPayload(BaseModel):
    action: str # delete, archive, unarchive, activate, deactivate
    ids: List[str]

class CategoryAdminPayload(BaseModel):
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    status: str = "active"

class OrderStatusUpdatePayload(BaseModel):
    shipping_status: str # pending, packed, shipped, delivered, cancelled
    payment_status: Optional[str] = None # pending, paid, failed

class CustomerStatusPayload(BaseModel):
    status: str # active, blocked

class UploadUrlPayload(BaseModel):
    url: str
    folder: Optional[str] = None

class ExecuteImportPayload(BaseModel):
    rows: List[Dict[str, Any]]
    duplicate_action: str = "skip" # skip, update, reject
    upload_images_to_cloudinary: bool = False


# ==========================================
# 1. ADMIN AUTHENTICATION
# ==========================================

@router.post("/auth/login")
async def admin_login(payload: AdminLoginPayload, response: Response):
    """Admin login via username or email."""
    # Find by username or email
    admin = await Admin.find_one(Admin.username == payload.username) or await Admin.find_one(Admin.email == payload.username)
    
    if not admin or not verify_password(payload.password, admin.password_hash):
        return api_response(
            success=False,
            message="Invalid administrator credentials",
            status_code=401
        )
        
    if admin.status != "active":
        return api_response(
            success=False,
            message="Administrator account is inactive. Please contact system owner.",
            status_code=403
        )
        
    token = create_access_token({"sub": str(admin.id), "role": "admin"})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    
    return api_response(
        success=True,
        message="Admin authentication successful",
        data={
            "token": token,
            "admin": {
                "id": str(admin.id),
                "username": admin.username,
                "email": admin.email,
                "role": "admin"
            }
        }
    )

@router.get("/auth/me")
async def admin_get_me(admin: Admin = Depends(get_current_admin)):
    """Verifies admin token and returns current admin details."""
    return api_response(
        success=True,
        message="Admin session is valid",
        data={
            "id": str(admin.id),
            "username": admin.username,
            "email": admin.email,
            "role": "admin",
            "cloudinary_configured": is_cloudinary_configured()
        }
    )


# ==========================================
# 2. DASHBOARD ANALYTICS
# ==========================================

@router.get("/analytics", dependencies=[Depends(get_current_admin)])
async def get_dashboard_analytics():
    """Generates real-time metrics, charts, and low-stock alerts."""
    # Product stats
    total_products = await Product.count()
    active_products = await Product.find(Product.status == "active").count()
    archived_products = await Product.find(Product.status == "archived").count()
    low_stock_products = await Product.find({"stock": {"$lte": 5, "$gt": 0}}).count()
    out_of_stock_products = await Product.find({"stock": 0}).count()
    
    # Inventory Valuation
    all_products = await Product.find_all().to_list()
    inventory_value = sum(p.stock * p.sale_price for p in all_products)
    
    # Order stats
    total_orders = await Order.count()
    orders = await Order.find_all().sort("-created_at").to_list()
    
    revenue_orders = [o for o in orders if o.shipping_status != "cancelled"]
    total_revenue = sum(o.total for o in revenue_orders)
    
    order_status_counts = {
        "pending": sum(1 for o in orders if o.shipping_status == "pending"),
        "packed": sum(1 for o in orders if o.shipping_status == "packed"),
        "shipped": sum(1 for o in orders if o.shipping_status == "shipped"),
        "delivered": sum(1 for o in orders if o.shipping_status == "delivered"),
        "cancelled": sum(1 for o in orders if o.shipping_status == "cancelled")
    }
    
    # Customer stats
    total_customers = await User.count()
    active_customers = await User.find(User.status == "active").count()
    
    # 30-Day Revenue Trend (daily aggregation)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    sales_trend_dict: Dict[str, Dict[str, float]] = {}
    
    # Initialize past 14 days for clean visualization
    for i in range(14):
        day_str = (datetime.utcnow() - timedelta(days=13 - i)).strftime("%b %d")
        sales_trend_dict[day_str] = {"revenue": 0.0, "orders": 0}
        
    for o in orders:
        if o.created_at and o.created_at >= (datetime.utcnow() - timedelta(days=14)):
            day_str = o.created_at.strftime("%b %d")
            if day_str in sales_trend_dict:
                sales_trend_dict[day_str]["orders"] += 1
                if o.shipping_status != "cancelled":
                    sales_trend_dict[day_str]["revenue"] += o.total
                    
    sales_trend = [
        {"date": date, "revenue": round(data["revenue"], 2), "orders": data["orders"]}
        for date, data in sales_trend_dict.items()
    ]
    
    # Category Distribution
    categories = await Category.find_all().to_list()
    category_distribution = []
    for cat in categories:
        count = sum(1 for p in all_products if p.category.lower() == cat.name.lower())
        category_distribution.append({
            "name": cat.name,
            "product_count": count
        })
        
    # Recent 5 Orders formatted
    recent_orders = []
    for o in orders[:5]:
        recent_orders.append({
            "id": str(o.id),
            "order_number": f"ORD-{str(o.id)[-6:].upper()}",
            "customer_name": o.shipping_address.get("name", "Customer"),
            "customer_email": o.shipping_address.get("email", ""),
            "items_count": sum(i.get("quantity", 1) for i in o.items),
            "total": o.total,
            "shipping_status": o.shipping_status,
            "payment_status": o.payment_status,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""
        })
        
    # Low stock items list (up to 8 items)
    low_stock_items = [
        {
            "id": str(p.id),
            "name": p.name,
            "sku": p.sku,
            "stock": p.stock,
            "thumbnail": p.thumbnail,
            "category": p.category,
            "price": p.sale_price
        }
        for p in all_products if p.stock <= 5
    ][:8]
    
    return api_response(
        success=True,
        message="Analytics retrieved successfully",
        data={
            "metrics": {
                "total_revenue": round(total_revenue, 2),
                "total_orders": total_orders,
                "total_products": total_products,
                "active_products": active_products,
                "archived_products": archived_products,
                "low_stock_count": low_stock_products,
                "out_of_stock_count": out_of_stock_products,
                "total_customers": total_customers,
                "active_customers": active_customers,
                "inventory_valuation": round(inventory_value, 2)
            },
            "order_status_counts": order_status_counts,
            "sales_trend": sales_trend,
            "category_distribution": category_distribution,
            "recent_orders": recent_orders,
            "low_stock_items": low_stock_items,
            "cloudinary_enabled": is_cloudinary_configured()
        }
    )


# ==========================================
# 3. PRODUCTS MANAGEMENT
# ==========================================

@router.get("/products", dependencies=[Depends(get_current_admin)])
async def admin_get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    search: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    status: Optional[str] = "all", # all, active, inactive, archived
    stock_status: Optional[str] = "all", # all, in_stock, low_stock, out_of_stock
    sort_by: Optional[str] = "newest" # newest, oldest, price_asc, price_desc, stock_asc, stock_desc, name_asc
):
    """Admin product listing with complete search, filtering, and sorting."""
    query = {}
    
    if status and status != "all":
        query["status"] = status
        
    if category and category != "all":
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}
        
    if subcategory and subcategory != "all":
        query["subcategory"] = {"$regex": f"^{subcategory}$", "$options": "i"}
        
    if stock_status == "out_of_stock":
        query["stock"] = 0
    elif stock_status == "low_stock":
        query["stock"] = {"$gt": 0, "$lte": 5}
    elif stock_status == "in_stock":
        query["stock"] = {"$gt": 0}
        
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"sku": regex},
            {"brand": regex},
            {"tags": regex},
            {"category": regex}
        ]
        
    # Query building
    db_query = Product.find(query)
    
    if sort_by == "price_asc":
        db_query = db_query.sort("sale_price")
    elif sort_by == "price_desc":
        db_query = db_query.sort("-sale_price")
    elif sort_by == "stock_asc":
        db_query = db_query.sort("stock")
    elif sort_by == "stock_desc":
        db_query = db_query.sort("-stock")
    elif sort_by == "name_asc":
        db_query = db_query.sort("name")
    elif sort_by == "oldest":
        db_query = db_query.sort("created_at")
    else:
        db_query = db_query.sort("-created_at")
        
    total = await Product.find(query).count()
    skip = (page - 1) * limit
    products = await db_query.skip(skip).limit(limit).to_list()
    
    formatted = []
    for p in products:
        d = p.model_dump()
        d["id"] = str(p.id)
        d["created_at_formatted"] = p.created_at.strftime("%Y-%m-%d") if p.created_at else ""
        formatted.append(d)
        
    return api_response(
        success=True,
        message="Products fetched successfully",
        data={
            "products": formatted,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )

@router.post("/products", dependencies=[Depends(get_current_admin)])
async def admin_create_product(payload: ProductAdminCreate):
    """Creates a new product with full fields including variants and SEO."""
    # Validate SKU uniqueness
    sku = payload.sku.strip().upper()
    existing_sku = await Product.find_one(Product.sku == sku)
    if existing_sku:
        return api_response(
            success=False,
            message=f"A product with SKU '{sku}' already exists ({existing_sku.name})",
            status_code=400
        )
        
    # Generate unique slug
    slug = payload.slug or payload.name.lower().replace(" ", "-").replace("&", "and")
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    existing_slug = await Product.find_one(Product.slug == slug)
    if existing_slug:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
        
    product = Product(
        name=payload.name,
        slug=slug,
        description=payload.description,
        short_description=payload.short_description,
        category=payload.category,
        subcategory=payload.subcategory,
        brand=payload.brand,
        mrp=payload.mrp,
        sale_price=payload.sale_price,
        stock=payload.stock,
        sku=sku,
        tags=payload.tags,
        color=payload.color,
        size=payload.size,
        weight=payload.weight,
        dimensions=payload.dimensions,
        featured=payload.featured,
        trending=payload.trending,
        best_seller=payload.best_seller,
        status=payload.status,
        thumbnail=payload.thumbnail,
        gallery_images=payload.gallery_images,
        variants=payload.variants,
        seo=payload.seo
    )
    product.calculate_discount()
    await product.insert()
    
    d = product.model_dump()
    d["id"] = str(product.id)
    return api_response(
        success=True,
        message="Product created successfully",
        data=d,
        status_code=201
    )

@router.get("/products/{id}", dependencies=[Depends(get_current_admin)])
async def admin_get_product(id: str):
    """Fetches full product details for admin editing."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
    d = product.model_dump()
    d["id"] = str(product.id)
    return api_response(success=True, message="Product fetched successfully", data=d)

@router.put("/products/{id}", dependencies=[Depends(get_current_admin)])
async def admin_update_product(id: str, payload: ProductAdminUpdate):
    """Updates product fields."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
        
    update_data = payload.model_dump(exclude_unset=True)
    
    # If SKU changed, verify uniqueness
    if "sku" in update_data and update_data["sku"]:
        new_sku = update_data["sku"].strip().upper()
        if new_sku != product.sku:
            existing = await Product.find_one(Product.sku == new_sku)
            if existing:
                return api_response(
                    success=False,
                    message=f"A product with SKU '{new_sku}' already exists",
                    status_code=400
                )
            update_data["sku"] = new_sku
            
    for k, v in update_data.items():
        setattr(product, k, v)
        
    product.updated_at = datetime.utcnow()
    product.calculate_discount()
    await product.save()
    
    d = product.model_dump()
    d["id"] = str(product.id)
    return api_response(success=True, message="Product updated successfully", data=d)

@router.delete("/products/{id}", dependencies=[Depends(get_current_admin)])
async def admin_delete_product(id: str):
    """Deletes a product."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
    await product.delete()
    return api_response(success=True, message=f"Product '{product.name}' deleted successfully")

@router.post("/products/{id}/duplicate", dependencies=[Depends(get_current_admin)])
async def admin_duplicate_product(id: str):
    """Duplicates an existing product with -COPY SKU and inactive status."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
        
    timestamp = int(datetime.utcnow().timestamp())
    new_sku = f"{product.sku}-COPY-{str(timestamp)[-4:]}"
    new_slug = f"{product.slug}-copy-{str(timestamp)[-4:]}"
    
    copy_product = Product(
        name=f"{product.name} (Copy)",
        slug=new_slug,
        description=product.description,
        short_description=product.short_description,
        category=product.category,
        subcategory=product.subcategory,
        brand=product.brand,
        mrp=product.mrp,
        sale_price=product.sale_price,
        stock=product.stock,
        sku=new_sku,
        tags=list(set(product.tags + ["copy"])),
        color=product.color,
        size=product.size,
        weight=product.weight,
        dimensions=product.dimensions,
        featured=False,
        trending=False,
        best_seller=False,
        status="inactive", # Default inactive so admin reviews before publishing
        thumbnail=product.thumbnail,
        gallery_images=product.gallery_images,
        variants=product.variants,
        seo=product.seo
    )
    copy_product.calculate_discount()
    await copy_product.insert()
    
    d = copy_product.model_dump()
    d["id"] = str(copy_product.id)
    return api_response(
        success=True,
        message=f"Product duplicated successfully as '{copy_product.name}'",
        data=d,
        status_code=201
    )

@router.patch("/products/{id}/status", dependencies=[Depends(get_current_admin)])
async def admin_update_product_status(id: str, payload: ProductStatusUpdate):
    """Quickly toggles status between active, inactive, or archived."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
        
    product.status = payload.status
    product.updated_at = datetime.utcnow()
    await product.save()
    
    return api_response(
        success=True,
        message=f"Product status updated to '{payload.status}'",
        data={"id": str(product.id), "status": product.status}
    )

@router.patch("/products/{id}/stock", dependencies=[Depends(get_current_admin)])
async def admin_update_product_stock(id: str, payload: ProductStockUpdate):
    """Quickly updates stock level for a product."""
    product = await Product.get(id)
    if not product:
        return api_response(success=False, message="Product not found", status_code=404)
        
    product.stock = payload.stock
    product.updated_at = datetime.utcnow()
    await product.save()
    
    return api_response(
        success=True,
        message=f"Stock updated to {payload.stock}",
        data={"id": str(product.id), "stock": product.stock}
    )

@router.post("/products/bulk-action", dependencies=[Depends(get_current_admin)])
async def admin_products_bulk_action(payload: BulkActionPayload):
    """Performs bulk actions across selected product IDs."""
    if not payload.ids:
        return api_response(success=False, message="No products selected", status_code=400)
        
    count = 0
    for pid in payload.ids:
        p = await Product.get(pid)
        if not p:
            continue
        if payload.action == "delete":
            await p.delete()
        elif payload.action == "archive":
            p.status = "archived"
            await p.save()
        elif payload.action == "unarchive" or payload.action == "activate":
            p.status = "active"
            await p.save()
        elif payload.action == "deactivate":
            p.status = "inactive"
            await p.save()
        count += 1
        
    return api_response(
        success=True,
        message=f"Bulk action '{payload.action}' applied to {count} products."
    )


# ==========================================
# 4. CATEGORIES & SUBCATEGORIES
# ==========================================

@router.get("/categories", dependencies=[Depends(get_current_admin)])
async def admin_get_categories():
    """Returns categories and subcategories hierarchy along with product counts."""
    categories = await Category.find_all().sort("name").to_list()
    products = await Product.find_all().to_list()
    
    # Calculate product count per category
    counts_map = {}
    for p in products:
        cname = (p.category or "").strip().lower()
        counts_map[cname] = counts_map.get(cname, 0) + 1
        
    cat_list = []
    for c in categories:
        d = c.model_dump()
        d["id"] = str(c.id)
        d["product_count"] = counts_map.get(c.name.lower(), 0)
        cat_list.append(d)
        
    return api_response(
        success=True,
        message="Categories fetched successfully",
        data=cat_list
    )

@router.post("/categories", dependencies=[Depends(get_current_admin)])
async def admin_create_category(payload: CategoryAdminPayload):
    """Creates a new category or subcategory."""
    slug = payload.slug or payload.name.lower().replace(" ", "-").replace("&", "and")
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    
    existing = await Category.find_one(Category.slug == slug)
    if existing:
        return api_response(
            success=False,
            message=f"Category with slug '{slug}' already exists",
            status_code=400
        )
        
    category = Category(
        name=payload.name,
        slug=slug,
        parent_id=payload.parent_id,
        description=payload.description,
        image=payload.image,
        icon=payload.icon,
        status=payload.status
    )
    await category.insert()
    
    d = category.model_dump()
    d["id"] = str(category.id)
    return api_response(
        success=True,
        message=f"Category '{category.name}' created successfully",
        data=d,
        status_code=201
    )

@router.put("/categories/{id}", dependencies=[Depends(get_current_admin)])
async def admin_update_category(id: str, payload: CategoryAdminPayload):
    """Updates a category or subcategory."""
    cat = await Category.get(id)
    if not cat:
        return api_response(success=False, message="Category not found", status_code=404)
        
    cat.name = payload.name
    if payload.slug:
        cat.slug = payload.slug
    cat.parent_id = payload.parent_id
    cat.description = payload.description
    if payload.image:
        cat.image = payload.image
    if payload.icon:
        cat.icon = payload.icon
    cat.status = payload.status
    cat.updated_at = datetime.utcnow()
    await cat.save()
    
    d = cat.model_dump()
    d["id"] = str(cat.id)
    return api_response(success=True, message="Category updated successfully", data=d)

@router.delete("/categories/{id}", dependencies=[Depends(get_current_admin)])
async def admin_delete_category(id: str):
    """Deletes category, verifying that no products are tied to it."""
    cat = await Category.get(id)
    if not cat:
        return api_response(success=False, message="Category not found", status_code=404)
        
    # Check if any products belong to this category
    prod_count = await Product.find({"$or": [{"category": cat.name}, {"category": cat.slug}]}).count()
    if prod_count > 0:
        return api_response(
            success=False,
            message=f"Cannot delete category '{cat.name}' because {prod_count} product(s) are assigned to it.",
            status_code=400
        )
        
    await cat.delete()
    return api_response(success=True, message=f"Category '{cat.name}' deleted successfully")


# ==========================================
# 5. INVENTORY MANAGEMENT
# ==========================================

@router.get("/inventory", dependencies=[Depends(get_current_admin)])
async def admin_get_inventory(
    filter_type: Optional[str] = "all", # all, low_stock, out_of_stock
    search: Optional[str] = None
):
    """Dedicated inventory view focusing on stock control."""
    query = {}
    if filter_type == "low_stock":
        query["stock"] = {"$gt": 0, "$lte": 5}
    elif filter_type == "out_of_stock":
        query["stock"] = 0
        
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [{"name": regex}, {"sku": regex}, {"category": regex}]
        
    products = await Product.find(query).sort("stock").to_list()
    
    all_products = await Product.find_all().to_list()
    total_items = sum(p.stock for p in all_products)
    total_val = sum(p.stock * p.sale_price for p in all_products)
    low_stock_count = sum(1 for p in all_products if 0 < p.stock <= 5)
    out_of_stock_count = sum(1 for p in all_products if p.stock == 0)
    
    formatted = []
    for p in products:
        d = p.model_dump()
        d["id"] = str(p.id)
        d["inventory_value"] = round(p.stock * p.sale_price, 2)
        formatted.append(d)
        
    return api_response(
        success=True,
        message="Inventory fetched successfully",
        data={
            "summary": {
                "total_products": len(all_products),
                "total_stock_units": total_items,
                "total_valuation": round(total_val, 2),
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count
            },
            "products": formatted
        }
    )


# ==========================================
# 6. ORDERS MANAGEMENT
# ==========================================

@router.get("/orders", dependencies=[Depends(get_current_admin)])
async def admin_get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    shipping_status: Optional[str] = "all",
    payment_status: Optional[str] = "all",
    search: Optional[str] = None
):
    """Lists customer orders with pagination, search, and status filters."""
    query = {}
    
    if shipping_status and shipping_status != "all":
        query["shipping_status"] = shipping_status
        
    if payment_status and payment_status != "all":
        query["payment_status"] = payment_status
        
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"shipping_address.name": regex},
            {"shipping_address.city": regex},
            {"shipping_address.phone": regex}
        ]
        
    total = await Order.find(query).count()
    skip = (page - 1) * limit
    orders = await Order.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    
    orders_list = []
    for o in orders:
        d = o.model_dump()
        d["id"] = str(o.id)
        d["order_number"] = f"ORD-{str(o.id)[-6:].upper()}"
        d["items_count"] = sum(i.get("quantity", 1) for i in o.items)
        d["created_at_formatted"] = o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""
        orders_list.append(d)
        
    return api_response(
        success=True,
        message="Orders fetched successfully",
        data={
            "orders": orders_list,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )

@router.get("/orders/{id}", dependencies=[Depends(get_current_admin)])
async def admin_get_order_detail(id: str):
    """Fetches comprehensive order details."""
    order = await Order.get(id)
    if not order:
        return api_response(success=False, message="Order not found", status_code=404)
        
    d = order.model_dump()
    d["id"] = str(order.id)
    d["order_number"] = f"ORD-{str(order.id)[-6:].upper()}"
    d["created_at_formatted"] = order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else ""
    return api_response(success=True, message="Order details fetched successfully", data=d)

@router.put("/orders/{id}/status", dependencies=[Depends(get_current_admin)])
async def admin_update_order_status(id: str, payload: OrderStatusUpdatePayload):
    """Updates order shipping and payment statuses."""
    order = await Order.get(id)
    if not order:
        return api_response(success=False, message="Order not found", status_code=404)
        
    order.shipping_status = payload.shipping_status
    if payload.payment_status:
        order.payment_status = payload.payment_status
    order.updated_at = datetime.utcnow()
    await order.save()
    
    return api_response(
        success=True,
        message=f"Order status updated to '{order.shipping_status}'",
        data={"id": str(order.id), "shipping_status": order.shipping_status, "payment_status": order.payment_status}
    )

@router.delete("/orders/{id}", dependencies=[Depends(get_current_admin)])
async def admin_delete_order(id: str):
    """Deletes an order."""
    order = await Order.get(id)
    if not order:
        return api_response(success=False, message="Order not found", status_code=404)
    await order.delete()
    return api_response(success=True, message="Order deleted successfully")


# ==========================================
# 7. CUSTOMERS MANAGEMENT
# ==========================================

@router.get("/customers", dependencies=[Depends(get_current_admin)])
async def admin_get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    status: Optional[str] = "all",
    search: Optional[str] = None
):
    """Lists customers with their lifetime orders and total spend."""
    query = {}
    if status and status != "all":
        query["status"] = status
        
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"email": regex},
            {"phone": regex}
        ]
        
    total = await User.find(query).count()
    skip = (page - 1) * limit
    users = await User.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    
    # Pre-fetch order stats
    orders = await Order.find_all().to_list()
    user_orders_map: Dict[str, List[Order]] = {}
    for o in orders:
        if o.user_id:
            user_orders_map.setdefault(o.user_id, []).append(o)
            
    customer_list = []
    for u in users:
        uid = str(u.id)
        u_orders = user_orders_map.get(uid, [])
        total_spend = sum(o.total for o in u_orders if o.shipping_status != "cancelled")
        
        customer_list.append({
            "id": uid,
            "name": u.name,
            "email": u.email,
            "phone": u.phone or "N/A",
            "address": u.address or "N/A",
            "status": u.status,
            "total_orders": len(u_orders),
            "total_spend": round(total_spend, 2),
            "joined_date": u.created_at.strftime("%b %d, %Y") if u.created_at else ""
        })
        
    return api_response(
        success=True,
        message="Customers fetched successfully",
        data={
            "customers": customer_list,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )

@router.patch("/customers/{id}/status", dependencies=[Depends(get_current_admin)])
async def admin_update_customer_status(id: str, payload: CustomerStatusPayload):
    """Blocks or unblocks a customer account."""
    user = await User.get(id)
    if not user:
        return api_response(success=False, message="Customer not found", status_code=404)
        
    user.status = payload.status
    user.updated_at = datetime.utcnow()
    await user.save()
    
    action = "unblocked" if payload.status == "active" else "blocked"
    return api_response(
        success=True,
        message=f"Customer '{user.name}' has been {action}.",
        data={"id": str(user.id), "status": user.status}
    )


# ==========================================
# 8. CLOUDINARY & IMAGE UPLOADS
# ==========================================

@router.post("/upload", dependencies=[Depends(get_current_admin)])
async def admin_upload_image(file: UploadFile = File(...)):
    """Uploads an image file to Cloudinary or falls back to local storage."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return api_response(success=False, message="File size exceeds maximum (10MB)", status_code=400)
        
    result = await upload_image_file(content, file.filename)
    return api_response(
        success=True,
        message="Image uploaded successfully",
        data=result
    )

@router.post("/upload-url", dependencies=[Depends(get_current_admin)])
async def admin_upload_image_url(payload: UploadUrlPayload):
    """Takes a remote image URL, downloads it, and uploads to Cloudinary."""
    if not payload.url:
        return api_response(success=False, message="Image URL is required", status_code=400)
        
    result = await upload_image_from_url(payload.url, payload.folder)
    return api_response(
        success=True,
        message="Image URL processed successfully",
        data=result
    )


# ==========================================
# 9. BULK EXCEL / CSV UPLOAD SYSTEM
# ==========================================

@router.get("/bulk/template")
async def download_bulk_template(format: str = Query("xlsx", pattern="^(xlsx|csv)$")):
    """Downloads pre-formatted Excel or CSV product import templates."""
    if format == "csv":
        data = generate_csv_template()
        headers = {
            "Content-Disposition": "attachment; filename=NB BEADS STUDIO_products_template.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
        return FastAPIResponse(content=data, headers=headers, media_type="text/csv")
    else:
        data = generate_excel_template()
        headers = {
            "Content-Disposition": "attachment; filename=NB BEADS STUDIO_products_template.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        return FastAPIResponse(
            content=data,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

@router.post("/bulk/validate", dependencies=[Depends(get_current_admin)])
async def validate_bulk_upload_file(file: UploadFile = File(...)):
    """Parses Excel or CSV, runs row-by-row validation, and returns preview."""
    content = await file.read()
    if not content:
        return api_response(success=False, message="Uploaded file is empty", status_code=400)
        
    try:
        report = await validate_bulk_file(content, file.filename)
        return api_response(
            success=True,
            message=f"Validation completed: {report['valid_count']} valid, {report['warning_count']} warnings, {report['error_count']} errors.",
            data=report
        )
    except Exception as e:
        return api_response(
            success=False,
            message=f"Failed to process file: {str(e)}",
            status_code=400
        )

@router.post("/bulk/import", dependencies=[Depends(get_current_admin)])
async def execute_bulk_products_import(payload: ExecuteImportPayload):
    """Executes bulk product import with duplicate SKU handling & Cloudinary migration."""
    if not payload.rows:
        return api_response(success=False, message="No rows provided for import", status_code=400)
        
    result = await execute_bulk_import(
        rows=payload.rows,
        duplicate_action=payload.duplicate_action,
        upload_images_to_cloudinary=payload.upload_images_to_cloudinary
    )
    
    return api_response(
        success=result.get("success", True),
        message=result.get("message", "Import executed"),
        data=result
    )


# ==========================================
# 10. IMAGE UPLOAD & URL PROCESSING
# ==========================================

@router.post("/upload", dependencies=[Depends(get_current_admin)])
async def admin_upload_image(file: UploadFile = File(...)):
    """Upload an image file directly to Cloudinary or local storage."""
    content = await file.read()
    if not content:
        return api_response(success=False, message="Empty image file received", status_code=400)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        return api_response(success=False, message="File size exceeds maximum allowed (10MB)", status_code=400)
    
    result = await upload_image_file(content, file.filename)
    return api_response(
        success=True,
        message="Product image uploaded successfully",
        data=result
    )

@router.post("/upload-url", dependencies=[Depends(get_current_admin)])
async def admin_upload_image_url(payload: UploadUrlPayload):
    """Import and cache an image from a remote URL."""
    if not payload.url or not payload.url.strip():
        return api_response(success=False, message="No URL provided", status_code=400)
    
    result = await upload_image_from_url(payload.url.strip(), payload.folder)
    return api_response(
        success=True,
        message="Remote product image processed successfully",
        data=result
    )
