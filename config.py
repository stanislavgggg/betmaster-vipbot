"""Environment settings + the brand/region catalogue."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str) -> list[int]:
    out: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            out.append(int(chunk))
    return out


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    admin_chat_ids: list[int]   # chats where requests land for review (group and/or admin DMs)
    vip_chat_id: int            # the VIP channel/group users get invited to
    vip_invite_link: str        # static fallback link used if the API call fails
    db_path: str
    brands_file: Path
    support_username: str
    auto_kick_expired: bool

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is not set")
        admin_ids = _int_list(os.getenv("ADMIN_IDS", ""))
        if not admin_ids:
            raise RuntimeError("ADMIN_IDS is not set (comma-separated Telegram user IDs)")
        # One group ID, or several IDs (admin DMs) separated by commas.
        # Falls back to ADMIN_IDS so requests always land somewhere.
        admin_chat_ids = _int_list(os.getenv("ADMIN_CHAT_ID", "")) or list(admin_ids)
        vip_chat = os.getenv("VIP_CHAT_ID", "").strip()
        if not vip_chat:
            raise RuntimeError("VIP_CHAT_ID is not set")
        return cls(
            bot_token=token,
            admin_ids=admin_ids,
            admin_chat_ids=admin_chat_ids,
            vip_chat_id=int(vip_chat),
            vip_invite_link=os.getenv("VIP_INVITE_LINK", "").strip(),
            db_path=os.getenv("DB_PATH", "bot.db"),
            brands_file=Path(os.getenv("BRANDS_FILE", "brands.json")),
            support_username=os.getenv("SUPPORT_USERNAME", "").lstrip("@"),
            auto_kick_expired=os.getenv("AUTO_KICK_EXPIRED", "true").lower() == "true",
        )


@dataclass(frozen=True)
class Brand:
    code: str
    name: str
    min_deposit: str
    link: str
    subid_param: str = "sub1"
    note: str = ""

    def tracking_link(self, user_id: int, source: str | None = None) -> str:
        """Append the Telegram user id as a sub id so postbacks can be matched back."""
        if not self.subid_param:
            return self.link
        params = {self.subid_param: str(user_id)}
        if source:
            params["sub2"] = source
        sep = "&" if "?" in self.link else "?"
        return f"{self.link}{sep}{urlencode(params)}"


@dataclass(frozen=True)
class Region:
    code: str
    title: str
    emoji: str
    brands: dict[str, Brand] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.title}"


class Catalog:
    """Loads brands.json. Reloadable at runtime with /reload."""

    def __init__(self, path: Path):
        self.path = path
        self.vip_name: str = "VIP"
        self.min_deposit: str = ""
        self.free_days: int = 30  # 0 = access never expires
        self.regions: dict[str, Region] = {}
        self.load()

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        vip = data.get("vip", {})
        base_brands = data.get("brands", {})

        regions: dict[str, Region] = {}
        for entry in data.get("regions", []):
            brands: dict[str, Brand] = {}
            for item in entry.get("brands", []):
                override: dict = {}
                if isinstance(item, str):
                    code = item
                else:
                    override = dict(item)
                    code = override.pop("code")
                base = base_brands.get(code)
                if base is None:
                    raise ValueError(f"Region '{entry['code']}' references unknown brand '{code}'")
                merged = {**base, **override}
                brands[code] = Brand(
                    code=code,
                    name=merged["name"],
                    min_deposit=merged.get("min_deposit", ""),
                    link=merged["link"],
                    subid_param=merged.get("subid_param", "sub1"),
                    note=merged.get("note", ""),
                )
            regions[entry["code"]] = Region(
                code=entry["code"],
                title=entry["title"],
                emoji=entry.get("emoji", ""),
                brands=brands,
            )

        self.vip_name = vip.get("name", "VIP")
        self.min_deposit = vip.get("min_deposit", "")
        self.free_days = int(vip.get("free_days", 30))
        self.regions = regions

    def region(self, code: str) -> Region | None:
        return self.regions.get(code)

    def brand(self, region_code: str, brand_code: str) -> Brand | None:
        region = self.regions.get(region_code)
        return region.brands.get(brand_code) if region else None

    def brand_name(self, region_code: str, brand_code: str) -> str:
        brand = self.brand(region_code, brand_code)
        return brand.name if brand else brand_code.title()


settings = Settings.from_env()
catalog = Catalog(settings.brands_file)
