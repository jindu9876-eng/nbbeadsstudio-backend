from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.models.setting import SystemSetting, get_or_create_settings, set_cached_hide_price_and_cart
from backend.routes.dependencies import get_current_admin
from backend.utils.response import api_response

router = APIRouter(tags=["Settings"])

class SettingsUpdatePayload(BaseModel):
    hide_price_and_cart: Optional[bool] = None

@router.get("/settings")
async def get_public_settings():
    """Public endpoint to fetch current storefront settings (e.g. Catalog Mode)."""
    setting = await get_or_create_settings()
    return api_response(
        success=True,
        message="Settings retrieved",
        data={
            "hide_price_and_cart": bool(setting.hide_price_and_cart)
        }
    )

@router.get("/admin/settings", dependencies=[Depends(get_current_admin)])
async def get_admin_settings():
    """Admin endpoint to fetch detailed system settings."""
    setting = await get_or_create_settings()
    return api_response(
        success=True,
        message="System settings retrieved",
        data={
            "hide_price_and_cart": bool(setting.hide_price_and_cart),
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        }
    )

@router.patch("/admin/settings", dependencies=[Depends(get_current_admin)])
@router.put("/admin/settings", dependencies=[Depends(get_current_admin)])
async def update_settings(payload: SettingsUpdatePayload):
    """Admin endpoint to update system settings."""
    setting = await get_or_create_settings()
    if payload.hide_price_and_cart is not None:
        setting.hide_price_and_cart = payload.hide_price_and_cart
        
    setting.updated_at = datetime.utcnow()
    await setting.save()
    set_cached_hide_price_and_cart(setting.hide_price_and_cart)
    
    return api_response(
        success=True,
        message="System settings updated successfully",
        data={
            "hide_price_and_cart": bool(setting.hide_price_and_cart),
            "updated_at": setting.updated_at.isoformat()
        }
    )

@router.post("/admin/settings/toggle-price-cart", dependencies=[Depends(get_current_admin)])
async def toggle_price_and_cart():
    """Admin endpoint to quickly toggle catalog mode on/off."""
    setting = await get_or_create_settings()
    setting.hide_price_and_cart = not bool(setting.hide_price_and_cart)
    setting.updated_at = datetime.utcnow()
    await setting.save()
    set_cached_hide_price_and_cart(setting.hide_price_and_cart)
    
    state_desc = "Catalog Mode enabled (Prices and Cart hidden)" if setting.hide_price_and_cart else "Store Mode enabled (Prices and Cart visible)"
    return api_response(
        success=True,
        message=state_desc,
        data={
            "hide_price_and_cart": bool(setting.hide_price_and_cart)
        }
    )
