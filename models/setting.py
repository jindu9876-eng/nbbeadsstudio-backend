from datetime import datetime
from typing import Optional
from backend.pg_engine import Document
from pydantic import Field

_cached_hide_price_and_cart: bool = False

def get_cached_hide_price_and_cart() -> bool:
    global _cached_hide_price_and_cart
    return _cached_hide_price_and_cart

def set_cached_hide_price_and_cart(val: bool):
    global _cached_hide_price_and_cart
    _cached_hide_price_and_cart = bool(val)

class SystemSetting(Document):
    key: str = "general"
    hide_price_and_cart: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "system_settings"
        indexes = ["key"]

async def get_or_create_settings() -> SystemSetting:
    setting = await SystemSetting.find_one(SystemSetting.key == "general")
    if not setting:
        setting = SystemSetting(key="general", hide_price_and_cart=False)
        await setting.insert()
    set_cached_hide_price_and_cart(setting.hide_price_and_cart)
    return setting

