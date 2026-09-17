"""BetsMaster-style VIP gate bot.

Flow: /start -> region -> partner brand -> tracked link -> deposit screenshot
      -> admin approve/reject -> one-time invite link to the VIP channel.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

import db as store
import keyboards as kb
import texts as t
from config import catalog, settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("vipbot")

router = Router()
database = store.Database(settings.db_path)


# --------------------------------------------------------------------------- helpers

def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


def fmt_ts(ts: int | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def support_suffix() -> str:
    if settings.support_username:
        return t.SUPPORT_SUFFIX.format(username=settings.support_username)
    return ""


async def safe_send(bot: Bot, chat_id: int, text: str, **kwargs) -> Message | None:
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramForbiddenError:
        log.info("User %s has blocked the bot", chat_id)
    except TelegramAPIError as exc:
        log.warning("send_message to %s failed: %s", chat_id, exc)
    return None


async def make_invite(bot: Bot, name: str) -> str | None:
    """Personal one-time link; falls back to the static VIP_INVITE_LINK if the API refuses."""
    try:
        link = await bot.create_chat_invite_link(
            settings.vip_chat_id,
            name=name,
            member_limit=1,
            expire_date=datetime.now(tz=timezone.utc) + timedelta(hours=24),
        )
        return link.invite_link
    except TelegramAPIError as exc:
        log.error("Invite link '%s' failed: %s — falling back to the static link", name, exc)
    return settings.vip_invite_link or None


async def render_request_caption(request: store.Request) -> str:
    """Caption shown in every admin chat for a request."""
    user_row = await database.get_user(request.user_id)
    region = catalog.region(request.region)
    username = user_row["username"] if user_row and user_row["username"] else None
    return t.ADMIN_REQUEST.format(
        rid=request.id,
        name=(user_row["first_name"] if user_row and user_row["first_name"] else "—"),
        user_id=request.user_id,
        username=f"@{username}" if username else "",
        region=region.title if region else request.region,
        brand=catalog.brand_name(request.region, request.brand_code),
        source=(user_row["source"] if user_row and user_row["source"] else "direct"),
        created=fmt_ts(request.created_at),
    )


async def fanout_to_admins(bot: Bot, request: store.Request, file_id: str, caption: str) -> int:
    """Post the request to every admin chat. Returns how many copies were delivered."""
    delivered = 0
    for chat_id in settings.admin_chat_ids:
        try:
            sent = await bot.send_photo(
                chat_id,
                photo=file_id,
                caption=caption,
                reply_markup=kb.review_kb(request.id),
            )
            await database.add_admin_message(request.id, sent.chat.id, sent.message_id)
            delivered += 1
        except TelegramForbiddenError:
            log.warning("Admin chat %s unreachable — they must /start the bot first", chat_id)
        except TelegramAPIError as exc:
            log.error("Could not post request #%s to %s: %s", request.id, chat_id, exc)
    if not delivered:
        log.error("Request #%s reached nobody — check ADMIN_CHAT_ID", request.id)
    return delivered


async def close_admin_copies(bot: Bot, request: store.Request, stamp: str) -> None:
    """After a decision, stamp every copy and strip the buttons so nobody double-handles it."""
    caption = await render_request_caption(request) + stamp
    for chat_id, message_id in await database.admin_messages(request.id):
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption,
                reply_markup=None,
            )
        except TelegramAPIError as exc:
            log.debug("Could not update copy %s/%s: %s", chat_id, message_id, exc)


async def send_main_menu(message: Message) -> None:
    await message.answer(
        t.WELCOME.format(vip_name=catalog.vip_name),
        reply_markup=kb.main_menu(catalog.regions),
    )


async def send_brand_card(message: Message, region_code: str, brand_code: str,
                          user_id: int, source: str | None) -> None:
    brand = catalog.brand(region_code, brand_code)
    if brand is None:
        return
    url = brand.tracking_link(user_id, source)
    note = f"ℹ️ {brand.note}\n" if brand.note else ""
    await message.answer(
        t.BRAND_CARD.format(
            brand=brand.name,
            min_deposit=brand.min_deposit or catalog.min_deposit or "—",
            link=url,
            note=note,
        ),
        reply_markup=kb.brand_card_kb(url),
        disable_web_page_preview=True,
    )


async def open_request(message: Message, region_code: str, brand_code: str,
                       user_id: int, source: str | None) -> bool:
    """Create an awaiting-screenshot request unless one already exists."""
    existing = await database.brand_request(
        user_id, region_code, brand_code, (store.APPROVED,)
    )
    if existing:
        await message.answer(
            t.ALREADY_APPROVED.format(brand=catalog.brand_name(region_code, brand_code))
        )
        return False

    existing = await database.brand_request(
        user_id, region_code, brand_code, store.OPEN_STATUSES
    )
    if existing:
        await send_brand_card(message, region_code, brand_code, user_id, source)
        await message.answer(
            t.ALREADY_REQUESTED.format(brand=catalog.brand_name(region_code, brand_code))
        )
        return False

    await database.create_request(user_id, region_code, brand_code)
    await send_brand_card(message, region_code, brand_code, user_id, source)
    return True


# --------------------------------------------------------------------------- user flow

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject | None = None) -> None:
    source = (command.args if command else None) or None
    user = message.from_user
    if user is None:
        return
    await database.upsert_user(user.id, user.username, user.first_name, source)
    await send_main_menu(message)

    pending = await database.next_awaiting(user.id)
    if pending:
        await message.answer(
            t.PENDING_HINT.format(
                brand=catalog.brand_name(pending.region, pending.brand_code)
            )
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await send_main_menu(message)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    if message.from_user is None:
        return
    count = await database.cancel_open(message.from_user.id)
    await message.answer(t.CANCELLED.format(count=count), reply_markup=kb.main_menu(catalog.regions))


@router.callback_query(F.data == "nav:menu")
async def cb_menu(call: CallbackQuery) -> None:
    await call.answer()
    if isinstance(call.message, Message):
        await send_main_menu(call.message)


@router.callback_query(F.data.in_({"menu:vip", "nav:regions"}))
async def cb_regions(call: CallbackQuery) -> None:
    await call.answer()
    if isinstance(call.message, Message):
        await call.message.answer(t.CHOOSE_REGION, reply_markup=kb.regions_kb(catalog.regions))


@router.callback_query(F.data.startswith("reg:"))
async def cb_region_selected(call: CallbackQuery) -> None:
    await call.answer()
    if not isinstance(call.message, Message) or call.from_user is None:
        return
    region_code = call.data.split(":", 1)[1]
    region = catalog.region(region_code)
    if region is None:
        await call.message.answer("That region is no longer available.",
                                  reply_markup=kb.regions_kb(catalog.regions))
        return
    await database.set_region(call.from_user.id, region_code)
    await call.message.answer(
        t.REGION_SELECTED.format(min_deposit=catalog.min_deposit or "—"),
        reply_markup=kb.brands_kb(region),
    )


@router.callback_query(F.data.startswith("brand:"))
async def cb_brand_selected(call: CallbackQuery) -> None:
    await call.answer()
    if not isinstance(call.message, Message) or call.from_user is None:
        return

    _, region_code, brand_code = call.data.split(":", 2)
    region = catalog.region(region_code)
    if region is None:
        await call.message.answer("That region is no longer available.",
                                  reply_markup=kb.regions_kb(catalog.regions))
        return

    user_row = await database.get_user(call.from_user.id)
    source = user_row["source"] if user_row else None
    user_id = call.from_user.id

    if brand_code == kb.ALL_BRANDS:
        opened: list[str] = []
        for code in region.brands:
            if await open_request(call.message, region_code, code, user_id, source):
                opened.append(region.brands[code].name)
        if opened:
            await call.message.answer(t.ALL_BRANDS_STARTED.format(brands=", ".join(opened)))
        return

    if brand_code not in region.brands:
        await call.message.answer("That brand is no longer available.",
                                  reply_markup=kb.brands_kb(region))
        return

    if await open_request(call.message, region_code, brand_code, user_id, source):
        await call.message.answer(
            t.PENDING_HINT.format(brand=region.brands[brand_code].name)
        )


@router.callback_query(F.data == "menu:pending")
async def cb_pending(call: CallbackQuery) -> None:
    await call.answer()
    if not isinstance(call.message, Message) or call.from_user is None:
        return
    requests = await database.open_requests(call.from_user.id)
    if not requests:
        await call.message.answer(t.NO_OPEN_REQUESTS, reply_markup=kb.main_menu(catalog.regions))
        return
    lines = [t.OPEN_REQUESTS_HEADER]
    for req in requests:
        icon = "⏳" if req.status == store.AWAITING else "🔍"
        state = t.REQ_WAITING if req.status == store.AWAITING else t.REQ_REVIEW
        lines.append(
            f"{icon} <b>{catalog.brand_name(req.region, req.brand_code)}</b> — {state}"
        )
    await call.message.answer("\n".join(lines), reply_markup=kb.main_menu(catalog.regions))


@router.callback_query(F.data == "menu:cancel")
async def cb_cancel(call: CallbackQuery) -> None:
    await call.answer()
    if not isinstance(call.message, Message) or call.from_user is None:
        return
    count = await database.cancel_open(call.from_user.id)
    await call.message.answer(t.CANCELLED.format(count=count), reply_markup=kb.main_menu(catalog.regions))


# --------------------------------------------------------------------------- screenshots

@router.message(F.chat.type == "private", F.photo | F.document.mime_type.startswith("image/"))
async def on_screenshot(message: Message, bot: Bot) -> None:
    user = message.from_user
    if user is None:
        return

    request = await database.next_awaiting(user.id)
    if request is None:
        await message.answer(t.NO_PENDING_FOR_PHOTO, reply_markup=kb.main_menu(catalog.regions))
        return

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    await database.attach_photo(request.id, file_id)

    brand_name = catalog.brand_name(request.region, request.brand_code)
    caption = await render_request_caption(request)
    await fanout_to_admins(bot, request, file_id, caption)

    reply = t.SCREENSHOT_RECEIVED.format(brand=brand_name)
    nxt = await database.next_awaiting(user.id)
    if nxt:
        reply += t.SCREENSHOT_NEXT.format(
            brand=catalog.brand_name(nxt.region, nxt.brand_code)
        )
    await message.answer(reply, reply_markup=kb.main_menu(catalog.regions))


@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def on_text(message: Message) -> None:
    if message.from_user is None:
        return
    pending = await database.next_awaiting(message.from_user.id)
    if pending:
        await message.answer(
            t.PENDING_HINT.format(
                brand=catalog.brand_name(pending.region, pending.brand_code)
            )
        )
    else:
        await send_main_menu(message)


# --------------------------------------------------------------------------- review

async def grant_access(bot: Bot, request: store.Request) -> None:
    brand_name = catalog.brand_name(request.region, request.brand_code)
    until = await database.grant_vip(request.user_id, catalog.free_days)

    invite = await make_invite(bot, f"req{request.id}")

    if invite and until:
        text = t.APPROVED_USER_UNTIL.format(
            brand=brand_name,
            vip_name=catalog.vip_name,
            invite=invite,
            until=fmt_ts(until),
        )
    elif invite:
        text = t.APPROVED_USER.format(
            brand=brand_name,
            vip_name=catalog.vip_name,
            invite=invite,
        )
    else:
        text = t.APPROVED_NO_LINK.format(brand=brand_name)
    await safe_send(bot, request.user_id, text, disable_web_page_preview=True)


@router.callback_query(F.data.startswith("adm:"))
async def cb_review(call: CallbackQuery, bot: Bot) -> None:
    if not is_admin(call.from_user.id):
        await call.answer(t.ADMIN_ONLY, show_alert=True)
        return

    _, action, raw_id = call.data.split(":", 2)
    request = await database.get_request(int(raw_id))
    if request is None:
        await call.answer("Request not found.", show_alert=True)
        return
    if request.status != store.PENDING:
        await call.answer(f"Already {request.status}.", show_alert=True)
        return

    approved = action == "ok"
    await database.decide(request.id, store.APPROVED if approved else store.REJECTED,
                          call.from_user.id)

    if approved:
        await grant_access(bot, request)
    else:
        await safe_send(
            bot,
            request.user_id,
            t.REJECTED_USER.format(
                brand=catalog.brand_name(request.region, request.brand_code),
                support=support_suffix(),
            ),
        )

    stamp = t.ADMIN_DECIDED.format(
        icon="✅" if approved else "❌",
        status="Approved" if approved else "Rejected",
        admin=f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name,
        when=fmt_ts(store.now()),
    )
    await close_admin_copies(bot, request, stamp)
    await call.answer("Approved" if approved else "Rejected")


# --------------------------------------------------------------------------- admin panel

@router.message(Command("admin", "help"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer(t.ADMIN_HELP)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        f"Chat ID: <code>{message.chat.id}</code>\n"
        f"Your ID: <code>{message.from_user.id if message.from_user else '—'}</code>"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    s = await database.stats()
    await message.answer(
        "📊 <b>Stats</b>\n\n"
        f"Users: <b>{s.get('users', 0)}</b> (+{s.get('users_24h', 0)} in 24h)\n"
        f"Active VIPs: <b>{s.get('vip_active', 0)}</b>\n\n"
        f"⏳ Awaiting screenshot: {s.get(store.AWAITING, 0)}\n"
        f"🔍 Pending review: {s.get(store.PENDING, 0)}\n"
        f"✅ Approved: {s.get(store.APPROVED, 0)}\n"
        f"❌ Rejected: {s.get(store.REJECTED, 0)}\n"
        f"🚫 Cancelled: {s.get(store.CANCELLED, 0)}"
    )


@router.message(Command("brands"))
async def cmd_brands(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    rows = await database.brand_breakdown()
    if not rows:
        await message.answer("No requests yet.")
        return
    lines = ["🎰 <b>Requests per brand</b>\n"]
    for region, brand, total, approved in rows:
        lines.append(
            f"{region.upper()} · {catalog.brand_name(region, brand)}: "
            f"{total} total / {approved} approved"
        )
    await message.answer("\n".join(lines))


@router.message(Command("pending"))
async def cmd_pending(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    cur = await database.conn.execute(
        "SELECT * FROM requests WHERE status = ? ORDER BY id LIMIT 30", (store.PENDING,)
    )
    rows = await cur.fetchall()
    if not rows:
        await message.answer("Nothing waiting for review. 🎉")
        return
    lines = ["🔍 <b>Pending review</b>\n"]
    for r in rows:
        lines.append(
            f"#{r['id']} · <code>{r['user_id']}</code> · "
            f"{catalog.brand_name(r['region'], r['brand_code'])} · {fmt_ts(r['created_at'])}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("user"))
async def cmd_user(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /user &lt;telegram_id&gt;")
        return
    uid = int(command.args.strip())
    row = await database.get_user(uid)
    if row is None:
        await message.answer("User not found.")
        return
    requests = await database.open_requests(uid)
    open_txt = ", ".join(
        f"{catalog.brand_name(r.region, r.brand_code)} ({r.status})" for r in requests
    ) or "none"
    await message.answer(
        f"👤 <b>{row['first_name'] or ''}</b> "
        f"{'@' + row['username'] if row['username'] else ''}\n"
        f"ID: <code>{uid}</code>\n"
        f"Source: {row['source'] or 'direct'}\n"
        f"Region: {row['region'] or '—'}\n"
        f"Joined: {fmt_ts(row['created_at'])}\n"
        f"VIP until: {fmt_ts(row['vip_until'])} "
        f"({'active' if row['vip_active'] else 'inactive'})\n"
        f"Open requests: {open_txt}"
    )


@router.message(Command("note"))
async def cmd_note(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("Usage: /note &lt;request_id&gt; &lt;message&gt;")
        return
    request = await database.get_request(int(parts[0]))
    if request is None:
        await message.answer("Request not found.")
        return
    sent = await safe_send(bot, request.user_id, f"💬 {parts[1]}")
    await message.answer("Sent." if sent else "Could not deliver (user blocked the bot?).")


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit():
        await message.answer("Usage: /grant &lt;user_id&gt; [days]")
        return
    uid = int(parts[0])
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else catalog.free_days
    until = await database.grant_vip(uid, days)
    invite = await make_invite(bot, f"manual{uid}")
    if not invite:
        await message.answer(
            "Granted, but no invite could be produced — "
            "check the bot's admin rights in the VIP chat or set VIP_INVITE_LINK."
        )
        return
    await safe_send(
        bot, uid,
        (f"✅ VIP access granted until <b>{fmt_ts(until)}</b>.\n{invite}"
         if until else f"✅ VIP access granted.\n{invite}"),
        disable_web_page_preview=True,
    )
    await message.answer(
        f"Granted {'lifetime' if days <= 0 else str(days) + ' days'} "
        f"to <code>{uid}</code>, invite sent."
    )


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /revoke &lt;user_id&gt;")
        return
    uid = int(command.args.strip())
    await database.deactivate_vip(uid)
    try:
        await bot.ban_chat_member(settings.vip_chat_id, uid)
        await bot.unban_chat_member(settings.vip_chat_id, uid, only_if_banned=True)
        await message.answer(f"Access revoked for <code>{uid}</code>.")
    except TelegramAPIError as exc:
        await message.answer(f"Marked inactive, but removal failed: {exc}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not command.args:
        await message.answer("Usage: /broadcast &lt;text&gt;")
        return
    user_ids = await database.all_user_ids()
    await message.answer(f"Sending to {len(user_ids)} users…")
    ok = 0
    for uid in user_ids:
        if await safe_send(bot, uid, command.args):
            ok += 1
        await asyncio.sleep(0.05)  # ~20 msg/s, within Telegram limits
    await message.answer(f"Broadcast done: {ok}/{len(user_ids)} delivered.")


@router.message(Command("reload"))
async def cmd_reload(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    try:
        catalog.load()
        total = sum(len(r.brands) for r in catalog.regions.values())
        await message.answer(
            f"♻️ Reloaded: {len(catalog.regions)} regions, {total} brand slots."
        )
    except Exception as exc:  # noqa: BLE001 - surface config errors to the admin
        await message.answer(f"Reload failed: <code>{exc}</code>")


# --------------------------------------------------------------------------- watchdog

async def vip_watchdog(bot: Bot) -> None:
    """Every hour, drop members whose free period has ended."""
    while True:
        try:
            for row in await database.expired_vips():
                uid = row["user_id"]
                await database.deactivate_vip(uid)
                if settings.auto_kick_expired:
                    try:
                        await bot.ban_chat_member(settings.vip_chat_id, uid)
                        await bot.unban_chat_member(settings.vip_chat_id, uid,
                                                    only_if_banned=True)
                    except TelegramAPIError as exc:
                        log.warning("Could not remove expired user %s: %s", uid, exc)
                await safe_send(
                    bot, uid,
                    t.VIP_EXPIRED.format(vip_name=catalog.vip_name),
                    reply_markup=kb.main_menu(catalog.regions),
                )
        except Exception:  # noqa: BLE001 - never let the loop die
            log.exception("watchdog iteration failed")
        await asyncio.sleep(3600)


# --------------------------------------------------------------------------- entrypoint

async def main() -> None:
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await database.connect()
    me = await bot.get_me()
    log.info("Starting @%s | %d regions | %d admin chat(s): %s",
             me.username, len(catalog.regions),
             len(settings.admin_chat_ids),
             ", ".join(str(c) for c in settings.admin_chat_ids))

    watchdog = asyncio.create_task(vip_watchdog(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        watchdog.cancel()
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
