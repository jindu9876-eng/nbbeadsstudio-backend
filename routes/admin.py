from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os

from backend.models.product import Product
from backend.models.category import Category
from backend.models.user import User
from backend.models.order import Order
from backend.models.wishlist import Wishlist
from backend.models.cart import Cart
from backend.models.admin import Admin
from datetime import datetime
from backend.utils.security import verify_password, create_access_token
from backend.routes.dependencies import get_token_str, get_current_admin
from backend.utils.response import api_response

router = APIRouter(prefix="/admin", tags=["Admin Web UI"])

# Initialize templates path relative to backend directory
current_file_dir = os.path.dirname(os.path.abspath(__file__))
backend_root_dir = os.path.dirname(current_file_dir)
templates_dir = os.path.join(backend_root_dir, "templates")
if not os.path.exists(templates_dir):
    templates_dir = "templates"
templates = Jinja2Templates(directory=templates_dir)

_orig_template_response = Jinja2Templates.TemplateResponse

def _patched_template_response(self, *args, **kwargs):
    if args and isinstance(args[0], str):
        name = args[0]
        context = args[1] if len(args) > 1 else kwargs.get("context", {})
        if isinstance(context, dict) and "hide_price_and_cart" not in context:
            from backend.models.setting import get_cached_hide_price_and_cart
            context["hide_price_and_cart"] = get_cached_hide_price_and_cart()
        request = kwargs.get("request") or (context.get("request") if isinstance(context, dict) else None)
        status_code = kwargs.get("status_code", 200)
        headers = kwargs.get("headers")
        media_type = kwargs.get("media_type")
        background = kwargs.get("background")
        return _orig_template_response(
            self,
            request=request,
            name=name,
            context=context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background
        )
    return _orig_template_response(self, *args, **kwargs)

Jinja2Templates.TemplateResponse = _patched_template_response

async def get_optional_admin(token_str: Optional[str]) -> Optional[Admin]:
    if not token_str:
        return None
    from backend.utils.security import decode_access_token
    payload = decode_access_token(token_str)
    if not payload or payload.get("role") != "admin":
        return None
    admin_id = payload.get("sub")
    return await Admin.get(admin_id)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if admin:
        return RedirectResponse(url="/admin/dashboard")
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})

@router.post("/login", response_class=HTMLResponse)
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    admin = await Admin.find_one(Admin.username == username)
    if admin and verify_password(password, admin.password_hash):
        if admin.status != "active":
            return templates.TemplateResponse(
                "admin/login.html",
                {"request": request, "error": "Admin account is inactive"}
            )
            
        token = create_access_token({"sub": str(admin.id), "role": "admin"})
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return response
        
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": "Invalid username or password"}
    )

@router.get("/logout")
async def handle_logout():
    response = RedirectResponse(url="/admin/login")
    response.delete_cookie(key="access_token")
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    # Stats queries
    total_products = await Product.count()
    total_orders = await Order.count()
    total_users = await User.count()
    total_categories = await Category.count()
    
    # Total Revenue (sum totals where status is not cancelled)
    orders = await Order.find(Order.shipping_status != "cancelled").to_list()
    total_revenue = sum(o.total for o in orders)
    
    # Wishlist count (total count of all products in all wishlists)
    wishlists = await Wishlist.find_all().to_list()
    wishlist_count = sum(len(w.product_ids) for w in wishlists)
    
    # Cart items count (total quantities of all items in all carts)
    carts = await Cart.find_all().to_list()
    cart_count = sum(sum(item.get("quantity", 0) for item in c.items) for c in carts)
    
    # Lists
    latest_orders = await Order.find_all().sort("-created_at").limit(5).to_list()
    recent_products = await Product.find_all().sort("-created_at").limit(5).to_list()
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "admin": admin,
            "stats": {
                "products": total_products,
                "orders": total_orders,
                "revenue": f"₹{total_revenue:,.2f}",
                "users": total_users,
                "categories": total_categories,
                "wishlist": wishlist_count,
                "cart": cart_count
            },
            "latest_orders": latest_orders,
            "recent_products": recent_products
        }
    )

@router.get("/products", response_class=HTMLResponse)
async def products_list_page(
    request: Request,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    token_str: Optional[str] = Depends(get_token_str)
):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    query = {}
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"sku": regex},
            {"category": regex}
        ]
        
    total = await Product.find(query).count()
    products_db = await Product.find(query).sort("-created_at").skip((page - 1) * limit).limit(limit).to_list()
    
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "admin": admin,
            "products": products_db,
            "page": page,
            "limit": limit,
            "total": total,
            "search": search or "",
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )

@router.get("/products/add", response_class=HTMLResponse)
@router.get("/products/new", response_class=HTMLResponse)
async def add_product_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    categories_db = await Category.find_all().to_list()
    return templates.TemplateResponse(
        "admin/add_product.html",
        {
            "request": request,
            "admin": admin,
            "categories": categories_db
        }
    )

@router.get("/products/edit/{id}", response_class=HTMLResponse)
async def edit_product_page(request: Request, id: str, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    product = await Product.get(id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    categories_db = await Category.find_all().to_list()
    return templates.TemplateResponse(
        "admin/edit_product.html",
        {
            "request": request,
            "admin": admin,
            "product": product,
            "categories": categories_db
        }
    )

@router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    categories_db = await Category.find_all().sort("name").to_list()
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "admin": admin,
            "categories": categories_db
        }
    )

@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    orders_db = await Order.find_all().sort("-created_at").to_list()
    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "admin": admin,
            "orders": orders_db
        }
    )

@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, token_str: Optional[str] = Depends(get_token_str)):
    admin = await get_optional_admin(token_str)
    if not admin:
        return RedirectResponse(url="/admin/login")
        
    users_db = await User.find_all().sort("-created_at").to_list()
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "admin": admin,
            "users": users_db
        }
    )

@router.put("/users/{id}/status", dependencies=[Depends(get_current_admin)])
async def update_user_status(id: str, payload: dict):
    user = await User.get(id)
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    status = payload.get("status", "active")
    user.status = status
    user.updated_at = datetime.utcnow()
    await user.save()
    return api_response(success=True, message=f"User status updated to {status}")

@router.delete("/users/{id}", dependencies=[Depends(get_current_admin)])
async def delete_user(id: str):
    user = await User.get(id)
    if not user:
        return api_response(success=False, message="User not found", status_code=404)
    await user.delete()
    return api_response(success=True, message="User deleted successfully")

@router.post("/settings/toggle-price-cart")
async def toggle_price_and_cart_admin_web(
    request: Request,
    token_str: Optional[str] = Depends(get_token_str)
):
    admin = await get_optional_admin(token_str)
    if not admin:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    
    from backend.models.setting import get_or_create_settings, set_cached_hide_price_and_cart
    setting = await get_or_create_settings()
    setting.hide_price_and_cart = not bool(setting.hide_price_and_cart)
    setting.updated_at = datetime.utcnow()
    await setting.save()
    set_cached_hide_price_and_cart(setting.hide_price_and_cart)
    
    # If AJAX/fetch request, return JSON
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if "application/json" in accept or "application/json" in content_type:
        from fastapi.responses import JSONResponse
        return JSONResponse(content={
            "success": True,
            "hide_price_and_cart": bool(setting.hide_price_and_cart),
            "message": "Catalog Mode enabled (Prices & Cart hidden)" if setting.hide_price_and_cart else "Store Mode enabled (Prices & Cart visible)"
        })
    
    referer = request.headers.get("referer") or "/admin/dashboard"
    return RedirectResponse(url=referer, status_code=303)
