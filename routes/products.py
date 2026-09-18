from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from datetime import datetime
from backend.models.product import Product
from backend.models.category import Category
from backend.schemas.api_schemas import ProductCreate, ProductUpdate
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_admin

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("")
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1),
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None, # "price_asc", "price_desc", "newest", "stock"
    featured: Optional[bool] = None,
    trending: Optional[bool] = None,
    best_seller: Optional[bool] = None
):
    # Base query
    query = {}
    
    # Filters
    if status:
        query["status"] = status
    else:
        # Default to active for normal queries
        query["status"] = "active"
        
    if category:
        # category could be slug or ID
        query["category"] = category
        
    if min_price is not None:
        query["sale_price"] = {"$gte": min_price}
        
    if max_price is not None:
        if "sale_price" in query:
            query["sale_price"]["$lte"] = max_price
        else:
            query["sale_price"] = {"$lte": max_price}
            
    if featured is not None:
        query["featured"] = featured
    if trending is not None:
        query["trending"] = trending
    if best_seller is not None:
        query["best_seller"] = best_seller
        
    if search:
        # Case insensitive text search on name, description, tags, sku
        regex_search = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex_search},
            {"description": regex_search},
            {"tags": regex_search},
            {"sku": regex_search}
        ]
        
    # Run query
    db_query = Product.find(query)
    
    # Sorting
    if sort_by == "price_asc":
        db_query = db_query.sort("sale_price")
    elif sort_by == "price_desc":
        db_query = db_query.sort("-sale_price")
    elif sort_by == "newest":
        db_query = db_query.sort("-created_at")
    elif sort_by == "stock":
        db_query = db_query.sort("-stock")
    else:
        # Default sort newest
        db_query = db_query.sort("-created_at")
        
    # Pagination
    total = await Product.find(query).count()
    skip = (page - 1) * limit
    products = await db_query.skip(skip).limit(limit).to_list()
    
    # Format list
    products_list = []
    for p in products:
        p_dict = p.model_dump()
        p_dict["id"] = str(p.id)
        # Formatted price for frontend compatibility (e.g. "₹899")
        p_dict["price"] = f"₹{p.sale_price:,.2f}".replace(".00", "")
        # Resolve image URL for storefront
        raw_img = p.thumbnail or (p.gallery_images[0] if p.gallery_images else "")
        if raw_img and raw_img.startswith("/") and not raw_img.startswith("//"):
            raw_img = f"http://localhost:8000{raw_img}"
        p_dict["image"] = raw_img
        if p.thumbnail and p.thumbnail.startswith("/") and not p.thumbnail.startswith("//"):
            p_dict["thumbnail"] = f"http://localhost:8000{p.thumbnail}"
        products_list.append(p_dict)
        
    return api_response(
        success=True,
        message="Products fetched successfully",
        data={
            "products": products_list,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )

@router.get("/{id}")
async def get_product_by_id(id: str):
    product = await Product.get(id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
    p_dict = product.model_dump()
    p_dict["id"] = str(product.id)
    p_dict["price"] = f"₹{product.sale_price:,.2f}".replace(".00", "")
    raw_img = product.thumbnail or (product.gallery_images[0] if product.gallery_images else "")
    if raw_img and raw_img.startswith("/") and not raw_img.startswith("//"):
        raw_img = f"http://localhost:8000{raw_img}"
    p_dict["image"] = raw_img
    if product.thumbnail and product.thumbnail.startswith("/") and not product.thumbnail.startswith("//"):
        p_dict["thumbnail"] = f"http://localhost:8000{product.thumbnail}"
    
    return api_response(
        success=True,
        message="Product details fetched successfully",
        data=p_dict
    )

@router.post("", dependencies=[Depends(get_current_admin)])
async def create_product(payload: ProductCreate):
    # Check unique SKU and slug
    existing_sku = await Product.find_one(Product.sku == payload.sku)
    if existing_sku:
        return api_response(
            success=False,
            message=f"Product with SKU '{payload.sku}' already exists",
            status_code=400
        )
        
    slug = payload.slug or payload.name.lower().replace(" ", "-").replace("&", "and")
    # Check unique slug
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
        sku=payload.sku,
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
        gallery_images=payload.gallery_images
    )
    product.calculate_discount()
    await product.insert()
    
    p_dict = product.model_dump()
    p_dict["id"] = str(product.id)
    
    return api_response(
        success=True,
        message="Product created successfully",
        data=p_dict,
        status_code=201
    )

@router.put("/{id}", dependencies=[Depends(get_current_admin)])
async def update_product(id: str, payload: ProductUpdate):
    product = await Product.get(id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
        
    update_data = payload.model_dump(exclude_unset=True)
    
    # Validate SKU if updated
    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = await Product.find_one(Product.sku == update_data["sku"])
        if existing:
            return api_response(
                success=False,
                message=f"Product with SKU '{update_data['sku']}' already exists",
                status_code=400
            )
            
    for key, value in update_data.items():
        setattr(product, key, value)
        
    product.updated_at = datetime.utcnow()
    product.calculate_discount()
    await product.save()
    
    p_dict = product.model_dump()
    p_dict["id"] = str(product.id)
    
    return api_response(
        success=True,
        message="Product updated successfully",
        data=p_dict
    )

@router.delete("/{id}", dependencies=[Depends(get_current_admin)])
async def delete_product(id: str):
    product = await Product.get(id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
        
    await product.delete()
    return api_response(
        success=True,
        message="Product deleted successfully"
    )

@router.post("/{id}/duplicate", dependencies=[Depends(get_current_admin)])
async def duplicate_product(id: str):
    product = await Product.get(id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
        
    # Generate unique SKU and slug
    timestamp = int(datetime.utcnow().timestamp())
    new_sku = f"{product.sku}-copy-{timestamp}"
    new_slug = f"{product.slug}-copy-{timestamp}"
    
    new_product = Product(
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
        tags=product.tags + ["copy"],
        color=product.color,
        size=product.size,
        weight=product.weight,
        dimensions=product.dimensions,
        featured=product.featured,
        trending=product.trending,
        best_seller=product.best_seller,
        status="inactive",  # Default duplicate to inactive
        thumbnail=product.thumbnail,
        gallery_images=product.gallery_images
    )
    new_product.calculate_discount()
    await new_product.insert()
    
    p_dict = new_product.model_dump()
    p_dict["id"] = str(new_product.id)
    
    return api_response(
        success=True,
        message="Product duplicated successfully",
        data=p_dict,
        status_code=201
    )
