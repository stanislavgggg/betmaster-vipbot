# VIP gate bot (BetsMaster flow)

Telegram bot that reproduces the @BETSMASTER_VIP_BOT flow:

```
/start → 🎰 Get VIP → region → partner brand → tracked link + min deposit
       → user deposits and sends a screenshot
       → admin group gets the screenshot with ✅ Approve / ❌ Reject
       → approve = one-time invite link to the VIP channel + N days of access
```

## What's in the box

| File | Purpose |
|---|---|
| `bot.py` | All handlers, admin panel, VIP expiry watchdog |
| `config.py` | Env settings + `brands.json` loader (hot-reloadable) |
| `db.py` | SQLite storage — users, requests, VIP expiry |
| `keyboards.py` | Inline keyboards |
| `texts.py` | Every user-facing string — swap this file to localise (LT / LV / ES) |
| `brands.json` | Regions, brands, min deposits, tracking links |

Request state lives in the DB, not in FSM memory, so a redeploy never loses a pending upload.

## Setup

1. **Bot** — create it with @BotFather, copy the token. In BotFather turn **Group Privacy off** only if you plan to read group messages (not needed here).
2. **Admin group** — create a private group, add the bot, post `/id` to get the chat ID (starts with `-100`).
3. **VIP channel** — add the bot as admin with **Invite users via link** and **Ban users** permissions. Post `/id` there (or forward a message) to get its ID.
4. **Your user ID** — send `/id` to the bot in DM.
5. Copy `.env.example` → `.env` and fill in the values.

```bash
pip install -r requirements.txt
python bot.py
```

## Railway deploy

- New project → deploy from repo → it picks up `Procfile` (`worker: python bot.py`).
- Add the env vars from `.env.example` in the Variables tab.
- **Attach a volume** mounted at `/data` and set `DB_PATH=/data/bot.db`. Without a volume the SQLite file is wiped on every redeploy and you lose VIP expiry dates.

## Editing offers

Everything lives in `brands.json`. A region lists brand codes, and can override any field per region:

```json
{ "code": "uk", "title": "UK", "brands": [
    "slotoro",
    { "code": "ggbet", "link": "https://ggbet-promo.com/l/UK_TRACKER" }
]}
```

Change the file, push, then send `/reload` in the admin group — no redeploy needed.

`free_days` under `vip` controls the free access period (30 = the "1-month free VIP" in the original bot).

## Tracking

Each brand card link gets `?sub1=<telegram_user_id>` appended, plus `sub2=<source>` when the user arrived via a deep link (`t.me/yourbot?start=propeller_push`). So:

- **sub1** ties an FTD postback back to the exact Telegram user who claimed VIP — you can match approvals against real deposits instead of trusting screenshots.
- **sub2** splits Propeller / Meta / channel traffic the same way the gate bot does.

Set `subid_param` per brand if a network uses a different parameter name (`sub_id`, `clickid`, etc.).

## Admin commands

```
/stats      users, requests, active VIPs
/brands     request breakdown per region + brand
/pending    open requests awaiting review
/user <id>  look up a user (source, region, VIP status, open requests)
/note <request_id> <text>   message the user about a request
/grant <user_id> [days]     grant VIP manually + send invite
/revoke <user_id>           end access and remove from the channel
/broadcast <text>           send to all users
/reload     reload brands.json
/id         show chat + user ID
```

## Behaviour notes

- **"Registered in all"** opens a request per brand in the region and queues them — each screenshot the user sends is matched to the next brand in the queue.
- **Duplicate protection**: one open request per brand per user; already-approved brands can't be claimed twice.
- **Expiry**: an hourly watchdog removes users whose free period ended (ban + immediate unban, so they can rejoin later) and messages them to renew. Set `AUTO_KICK_EXPIRED=false` to only notify.
- **Rejections** send a canned message; use `/note` to add a specific reason.
- Approving a second brand for the same user **extends** access rather than resetting it.

## Worth adding next

- Postback endpoint so an FTD from the network auto-approves the request — screenshots are trivially faked, and right now approval rests on a human eyeballing an image.
- Rejection reason buttons (wrong brand / no deposit visible / not our link) if volume grows past what `/note` handles comfortably.
