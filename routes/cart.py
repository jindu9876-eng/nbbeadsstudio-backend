from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from backend.models.cart import Cart
from backend.models.product import Product
from backend.schemas.api_schemas import CartItemUpdate
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_user

router = APIRouter(prefix="/cart", tags=["Cart"])

async def get_populated_cart(user_id: str) -> Dict[str, Any]:
    cart = await Cart.find_one(Cart.user_id == user_id)
    if not cart:
        cart = Cart(user_id=user_id, items=[])
        await cart.insert()
        
    populated_items = []
    for item in cart.items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        product = await Product.get(product_id)
        if product:
            populated_items.append({
                "id": str(product.id),
                "name": product.name,
                "price": f"₹{product.sale_price:,.2f}".replace(".00", ""),
                "image": product.thumbnail,
                "category": product.category,
                "description": product.description,
                "quantity": quantity
            })
            
    return {
        "items": populated_items,
        "cart_id": str(cart.id)
    }

@router.get("")
async def get_cart(current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    cart_data = await get_populated_cart(user_id)
    return api_response(
        success=True,
        message="Cart retrieved successfully",
        data=cart_data
    )

@router.post("")
async def add_to_cart(payload: CartItemUpdate, current_user = Depends(get_current_user)):
    # Check if catalog mode is active
    from backend.models.setting import get_or_create_settings
    settings_obj = await get_or_create_settings()
    if settings_obj.hide_price_and_cart:
        return api_response(
            success=False,
            message="Cart functionality is currently disabled by administrator (Catalog Mode).",
            status_code=400
        )

    user_id = str(current_user.id)
    # Check if product exists
    product = await Product.get(payload.product_id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
        
    cart = await Cart.find_one(Cart.user_id == user_id)
    if not cart:
        cart = Cart(user_id=user_id, items=[])
        await cart.insert()
        
    # Check if item already exists in cart
    item_index = -1
    for idx, item in enumerate(cart.items):
        if item["product_id"] == payload.product_id:
            item_index = idx
            break
            
    if item_index != -1:
        cart.items[item_index]["quantity"] += payload.quantity
    else:
        cart.items.append({
            "product_id": payload.product_id,
            "quantity": payload.quantity
        })
        
    await cart.save()
    cart_data = await get_populated_cart(user_id)
    return api_response(
        success=True,
        message="Product added to cart",
        data=cart_data
    )

@router.put("/{product_id}")
async def update_cart_item(
    product_id: str,
    payload: Dict[str, int], # {"quantity": int}
    current_user = Depends(get_current_user)
):
    user_id = str(current_user.id)
    quantity = payload.get("quantity", 1)
    
    cart = await Cart.find_one(Cart.user_id == user_id)
    if not cart:
        return api_response(
            success=False,
            message="Cart not found",
            status_code=404
        )
        
    item_index = -1
    for idx, item in enumerate(cart.items):
        if item["product_id"] == product_id:
            item_index = idx
            break
            
    if item_index == -1:
        return api_response(
            success=False,
            message="Item not found in cart",
            status_code=404
        )
        
    if quantity <= 0:
        cart.items.pop(item_index)
    else:
        cart.items[item_index]["quantity"] = quantity
        
    await cart.save()
    cart_data = await get_populated_cart(user_id)
    return api_response(
        success=True,
        message="Cart item updated",
        data=cart_data
    )

@router.delete("/{product_id}")
async def remove_from_cart(product_id: str, current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    
    cart = await Cart.find_one(Cart.user_id == user_id)
    if not cart:
        return api_response(
            success=False,
            message="Cart not found",
            status_code=404
        )
        
    cart.items = [item for item in cart.items if item["product_id"] != product_id]
    await cart.save()
    cart_data = await get_populated_cart(user_id)
    return api_response(
        success=True,
        message="Item removed from cart",
        data=cart_data
    )

@router.post("/clear")
async def clear_cart(current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    cart = await Cart.find_one(Cart.user_id == user_id)
    if cart:
        cart.items = []
        await cart.save()
    return api_response(
        success=True,
        message="Cart cleared successfully",
        data={"items": []}
    )
