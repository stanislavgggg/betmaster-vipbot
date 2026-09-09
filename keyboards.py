"""Inline keyboards. Callback data format: '<scope>:<arg>:<arg>'."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Region

ALL_BRANDS = "__all__"


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎰 Get VIP", callback_data="menu:vip")
    kb.button(text="📋 Pending Requests", callback_data="menu:pending")
    kb.button(text="❌ Cancel Requests", callback_data="menu:cancel")
    kb.adjust(2, 1)
    return kb.as_markup()


def regions_kb(regions: dict[str, Region]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for region in regions.values():
        kb.button(text=region.title, callback_data=f"reg:{region.code}")
    kb.button(text="⬅️ Back", callback_data="nav:menu")
    kb.adjust(4, 3, 1)
    return kb.as_markup()


def brands_kb(region: Region) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for brand in region.brands.values():
        kb.button(text=brand.name.upper(), callback_data=f"brand:{region.code}:{brand.code}")
    if len(region.brands) > 1:
        kb.button(text="🌍 Registered in all", callback_data=f"brand:{region.code}:{ALL_BRANDS}")
    kb.button(text="⬅️ Change region", callback_data="nav:regions")
    kb.adjust(3, 1, 1)
    return kb.as_markup()


def brand_card_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Register & deposit", url=url)],
            [InlineKeyboardButton(text="❌ Cancel this request", callback_data="menu:cancel")],
        ]
    )


def review_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"adm:ok:{request_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"adm:no:{request_id}"),
            ]
        ]
    )


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Main menu", callback_data="nav:menu")]]
    )
