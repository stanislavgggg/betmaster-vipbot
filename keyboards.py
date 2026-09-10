"""Inline keyboards. Callback data format: '<scope>:<arg>:<arg>'."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Region

ALL_BRANDS = "__all__"


def regions_kb(regions: dict[str, Region], with_extras: bool = True) -> InlineKeyboardMarkup:
    """Country picker. On /start it also carries the requests/cancel shortcuts."""
    kb = InlineKeyboardBuilder()
    for region in regions.values():
        label = f"{region.emoji} {region.title}".strip()
        kb.button(text=label, callback_data=f"reg:{region.code}")
    widths = [2] * (len(regions) // 2)
    if len(regions) % 2:
        widths.append(1)
    if with_extras:
        kb.button(text="📋 Moji zahtjevi", callback_data="menu:pending")
        kb.button(text="❌ Otkaži zahtjeve", callback_data="menu:cancel")
        widths.append(2)
    kb.adjust(*widths)
    return kb.as_markup()


def main_menu(regions: dict[str, Region]) -> InlineKeyboardMarkup:
    return regions_kb(regions, with_extras=True)


def brands_kb(region: Region) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for brand in region.brands.values():
        kb.button(text=brand.name, callback_data=f"brand:{region.code}:{brand.code}")
    widths = [2] * (len(region.brands) // 2)
    if len(region.brands) % 2:
        widths.append(1)
    if len(region.brands) > 1:
        kb.button(text="🌍 Registriran u svima", callback_data=f"brand:{region.code}:{ALL_BRANDS}")
        widths.append(1)
    kb.button(text="⬅️ Promijeni zemlju", callback_data="nav:regions")
    widths.append(1)
    kb.adjust(*widths)
    return kb.as_markup()


def brand_card_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Registriraj se i uplati", url=url)],
            [InlineKeyboardButton(text="⬅️ Ostali partneri", callback_data="nav:regions")],
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
