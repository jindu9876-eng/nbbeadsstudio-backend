from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from backend.models.wishlist import Wishlist
from backend.models.product import Product
from backend.schemas.api_schemas import WishlistUpdate
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_user

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

async def get_populated_wishlist(user_id: str) -> Dict[str, Any]:
    wishlist = await Wishlist.find_one(Wishlist.user_id == user_id)
    if not wishlist:
        wishlist = Wishlist(user_id=user_id, product_ids=[])
        await wishlist.insert()
        
    populated_products = []
    for pid in wishlist.product_ids:
        product = await Product.get(pid)
        if product:
            p_dict = product.model_dump()
            p_dict["id"] = str(product.id)
            p_dict["price"] = f"₹{product.sale_price:,.2f}".replace(".00", "")
            raw_img = product.thumbnail or (product.gallery_images[0] if product.gallery_images else "")
            if raw_img and raw_img.startswith("/") and not raw_img.startswith("//"):
                raw_img = f"http://localhost:8000{raw_img}"
            p_dict["image"] = raw_img
            if product.thumbnail and product.thumbnail.startswith("/") and not product.thumbnail.startswith("//"):
                p_dict["thumbnail"] = f"http://localhost:8000{product.thumbnail}"
            populated_products.append(p_dict)
            
    return {
        "products": populated_products,
        "wishlist_id": str(wishlist.id)
    }

@router.get("")
async def get_wishlist(current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    wishlist_data = await get_populated_wishlist(user_id)
    return api_response(
        success=True,
        message="Wishlist retrieved successfully",
        data=wishlist_data
    )

@router.post("")
async def add_to_wishlist(payload: WishlistUpdate, current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    # Check if product exists
    product = await Product.get(payload.product_id)
    if not product:
        return api_response(
            success=False,
            message="Product not found",
            status_code=404
        )
        
    wishlist = await Wishlist.find_one(Wishlist.user_id == user_id)
    if not wishlist:
        wishlist = Wishlist(user_id=user_id, product_ids=[])
        await wishlist.insert()
        
    if payload.product_id not in wishlist.product_ids:
        wishlist.product_ids.append(payload.product_id)
        await wishlist.save()
        
    wishlist_data = await get_populated_wishlist(user_id)
    return api_response(
        success=True,
        message="Product added to wishlist",
        data=wishlist_data
    )

@router.delete("/{product_id}")
async def remove_from_wishlist(product_id: str, current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    wishlist = await Wishlist.find_one(Wishlist.user_id == user_id)
    if not wishlist:
        return api_response(
            success=False,
            message="Wishlist not found",
            status_code=404
        )
        
    wishlist.product_ids = [pid for pid in wishlist.product_ids if pid != product_id]
    await wishlist.save()
    
    wishlist_data = await get_populated_wishlist(user_id)
    return api_response(
        success=True,
        message="Product removed from wishlist",
        data=wishlist_data
    )
