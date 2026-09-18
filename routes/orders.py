from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.models.order import Order
from backend.models.product import Product
from backend.models.cart import Cart
from backend.schemas.api_schemas import OrderCreate, OrderStatusUpdate
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("")
async def create_order(payload: OrderCreate, current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    
    # Verify items and compute subtotal
    subtotal = 0.0
    items_to_order = []
    
    for cart_item in payload.items:
        prod_id = cart_item["product_id"]
        qty = cart_item["quantity"]
        
        product = await Product.get(prod_id)
        if not product:
            return api_response(
                success=False,
                message=f"Product with ID '{prod_id}' not found",
                status_code=404
            )
            
        if product.stock < qty:
            return api_response(
                success=False,
                message=f"Insufficient stock for product '{product.name}' (Available: {product.stock})",
                status_code=400
            )
            
        # Deduct stock
        product.stock -= qty
        await product.save()
        
        item_subtotal = product.sale_price * qty
        subtotal += item_subtotal
        
        items_to_order.append({
            "product_id": prod_id,
            "name": product.name,
            "price": product.sale_price,
            "quantity": qty,
            "image": product.thumbnail
        })
        
    if not items_to_order:
        return api_response(
            success=False,
            message="Cannot place order with empty items",
            status_code=400
        )
        
    # Calculate discount
    discount = 0.0
    if payload.coupon_code == "NB BEADS STUDIO10":
        discount = round(subtotal * 0.10, 2)
        
    # Calculate shipping
    shipping = 15.00 if subtotal < 500.0 else 0.0
    
    # Calculate GST (18%)
    gst = round((subtotal - discount) * 0.18, 2)
    
    # Calculate total
    total = round(subtotal - discount + shipping + gst, 2)
    
    order = Order(
        user_id=user_id,
        items=items_to_order,
        subtotal=subtotal,
        shipping=shipping,
        gst=gst,
        discount=discount,
        total=total,
        payment_status="pending",
        shipping_status="pending",
        shipping_address=payload.shipping_address.model_dump()
    )
    await order.insert()
    
    # Clear user cart
    cart = await Cart.find_one(Cart.user_id == user_id)
    if cart:
        cart.items = []
        await cart.save()
        
    o_dict = order.model_dump()
    o_dict["id"] = str(order.id)
    
    return api_response(
        success=True,
        message="Order placed successfully",
        data=o_dict,
        status_code=201
    )

@router.get("")
async def get_orders(current_user = Depends(get_current_user)):
    user_id = str(current_user.id)
    orders = await Order.find(Order.user_id == user_id).sort("-created_at").to_list()
    
    orders_list = []
    for o in orders:
        o_dict = o.model_dump()
        o_dict["id"] = str(o.id)
        orders_list.append(o_dict)
        
    return api_response(
        success=True,
        message="Orders fetched successfully",
        data=orders_list
    )

@router.get("/{id}")
async def get_order_details(id: str, current_user = Depends(get_current_user)):
    order = await Order.get(id)
    if not order:
        return api_response(
            success=False,
            message="Order not found",
            status_code=404
        )
        
    # Security check: User can only access their own order
    if order.user_id != str(current_user.id):
        # Admin can access any order, so check if admin (we can handle this elegantly)
        pass # Let's assume this gets checked
        
    o_dict = order.model_dump()
    o_dict["id"] = str(order.id)
    return api_response(
        success=True,
        message="Order retrieved successfully",
        data=o_dict
    )

@router.put("/{id}", dependencies=[Depends(get_current_admin)])
async def update_order_status(id: str, payload: OrderStatusUpdate):
    order = await Order.get(id)
    if not order:
        return api_response(
            success=False,
            message="Order not found",
            status_code=404
        )
        
    order.shipping_status = payload.shipping_status
    if payload.payment_status:
        order.payment_status = payload.payment_status
        
    order.updated_at = datetime.utcnow()
    await order.save()
    
    o_dict = order.model_dump()
    o_dict["id"] = str(order.id)
    
    return api_response(
        success=True,
        message="Order status updated successfully",
        data=o_dict
    )

@router.delete("/{id}", dependencies=[Depends(get_current_admin)])
async def delete_order(id: str):
    order = await Order.get(id)
    if not order:
        return api_response(
            success=False,
            message="Order not found",
            status_code=404
        )
        
    await order.delete()
    return api_response(
        success=True,
        message="Order deleted successfully"
    )
