"""All user-facing copy lives here — swap this file to localise the bot (LT / LV / ES ...)."""

WELCOME = (
    "👋 <b>Welcome to {vip_name} Bot!</b>\n\n"
    "Choose an option below:"
)

CHOOSE_REGION = "Welcome! Please select your region:"

REGION_SELECTED = (
    "You selected <b>{region}</b> {emoji}\n\n"
    "Choose one of our partner brands to register and get your "
    "<b>{days}-day free VIP access</b>:"
)

BRAND_CARD = (
    "🎰 <b>Brand:</b> {brand}\n\n"
    "💰 <b>Minimum Deposit:</b> {min_deposit}\n"
    "🔗 <b>Link:</b> {link}\n"
    "{note}"
    "\n<b>Instructions:</b> Register through the link above, make your deposit, "
    "then send a screenshot here!"
)

PENDING_HINT = (
    "⏳ You have a pending screenshot request for <b>{brand}</b>. "
    "Send your screenshot or type /cancel to cancel."
)

ALL_BRANDS_STARTED = (
    "📋 Requests opened for: <b>{brands}</b>\n\n"
    "Send your screenshots one by one — I'll match each one to the next brand in the queue."
)

ALREADY_REQUESTED = (
    "ℹ️ You already have an open request for <b>{brand}</b>. "
    "Send the screenshot, or use ❌ Cancel Requests to start over."
)

ALREADY_APPROVED = "✅ <b>{brand}</b> is already approved for your account."

NO_OPEN_REQUESTS = "You have no open requests. Tap 🎰 Get VIP to start."

OPEN_REQUESTS_HEADER = "📋 <b>Your requests:</b>\n\n"

CANCELLED = "❌ Cancelled {count} pending request(s)."

SCREENSHOT_RECEIVED = (
    "📨 Screenshot for <b>{brand}</b> received and sent for review.\n"
    "You'll get a reply here as soon as it's checked."
)

SCREENSHOT_NEXT = "\n\n⏳ Next in queue: <b>{brand}</b>. Send that screenshot when ready."

NO_PENDING_FOR_PHOTO = (
    "I'm not expecting a screenshot right now. Tap 🎰 Get VIP, pick a brand, "
    "and send the screenshot after you deposit."
)

APPROVED_USER = (
    "✅ <b>Approved!</b> Your deposit on <b>{brand}</b> has been confirmed.\n\n"
    "Here is your personal invite link to {vip_name} (valid for 24 hours, one use only):\n"
    "{invite}\n\n"
    "Your access runs until <b>{until}</b>."
)

APPROVED_NO_LINK = (
    "✅ <b>Approved!</b> Your deposit on <b>{brand}</b> has been confirmed.\n\n"
    "There was a problem generating your invite link — an admin will send it manually shortly."
)

REJECTED_USER = (
    "❌ Your screenshot for <b>{brand}</b> could not be verified.\n\n"
    "Make sure the screenshot shows the deposit on an account registered "
    "through our link. You can send a new one by tapping 🎰 Get VIP.{support}"
)

VIP_EXPIRED = (
    "⌛ Your free {days}-day access to {vip_name} has ended.\n\n"
    "Tap 🎰 Get VIP to register with another partner brand and renew your access."
)

SUPPORT_SUFFIX = "\n\nQuestions? Write to @{username}."

ADMIN_ONLY = "This command is for admins only."

# ---- admin side ----

ADMIN_REQUEST = (
    "🆕 <b>VIP request #{rid}</b>\n\n"
    "👤 {name} (<code>{user_id}</code>) {username}\n"
    "🌍 Region: {region}\n"
    "🎰 Brand: <b>{brand}</b>\n"
    "🔖 Source: {source}\n"
    "🕒 {created}"
)

ADMIN_DECIDED = "\n\n{icon} <b>{status}</b> by {admin} at {when}"

ADMIN_HELP = (
    "<b>Admin panel</b>\n\n"
    "/stats — users, requests, active VIPs\n"
    "/brands — request breakdown per brand\n"
    "/pending — open requests awaiting review\n"
    "/user &lt;id&gt; — look up a user\n"
    "/note &lt;request_id&gt; &lt;text&gt; — message the user about a request\n"
    "/grant &lt;user_id&gt; [days] — grant VIP manually\n"
    "/revoke &lt;user_id&gt; — end VIP access and remove from the channel\n"
    "/broadcast &lt;text&gt; — send to all users\n"
    "/reload — reload brands.json without redeploy\n"
    "/id — show this chat's ID"
)
