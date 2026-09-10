"""User-facing copy (Croatian). Admin-side strings stay in English."""

# ---- user side (HR) ----

WELCOME = (
    "👋 Pozdrav, hvala vam na poruci i interesu za <b>{vip_name} grupu</b>.\n\n"
    "<b>Dobrodošli! Odaberite svoju zemlju:</b>"
)

CHOOSE_REGION = "<b>Odaberite svoju zemlju:</b>"

REGION_SELECTED = (
    "Kako biste se <b>BESPLATNO</b> pridružili VIP kanalu, potrebno je registrirati se "
    "kod jednog od partnera u nastavku i uplatiti minimalno <b>{min_deposit}</b>. "
    "Tako ćete moći pratiti i igrati iste oklade zajedno sa mnom. "
    "Za pristup VIP kanalu <b>nema dodatnih plaćanja</b>.\n\n"
    "👇 <b>Odaberite partnera kod kojeg se želite registrirati i ostvarite "
    "besplatan VIP pristup:</b>"
)

BRAND_CARD = (
    "🎰 <b>Brend:</b> {brand}\n\n"
    "💰 <b>Minimalna uplata:</b> {min_deposit}\n"
    "🔗 <b>Link:</b> <a href=\"{link}\">Registriraj se ovdje</a>\n"
    "{note}"
    "\n<b>Upute:</b> Registrirajte se putem poveznice iznad, uplatite minimalno "
    "{min_deposit}, a zatim ovdje pošaljite screenshot kao potvrdu."
)

PENDING_HINT = (
    "⏳ Čekamo vaš screenshot za <b>{brand}</b>. "
    "Pošaljite screenshot ili upišite /cancel za otkazivanje."
)

ALL_BRANDS_STARTED = (
    "📋 Otvoreni zahtjevi za: <b>{brands}</b>\n\n"
    "Šaljite screenshotove jedan po jedan — svaki ću povezati sa sljedećim brendom u redu."
)

ALREADY_REQUESTED = (
    "ℹ️ Već imate otvoren zahtjev za <b>{brand}</b>. "
    "Pošaljite screenshot ili odaberite ❌ Otkaži zahtjeve za novi početak."
)

ALREADY_APPROVED = "✅ <b>{brand}</b> je već odobren za vaš račun."

NO_OPEN_REQUESTS = "Nemate otvorenih zahtjeva. Odaberite zemlju ispod za početak."

OPEN_REQUESTS_HEADER = "📋 <b>Vaši zahtjevi:</b>\n\n"

REQ_WAITING = "čeka vaš screenshot"
REQ_REVIEW = "u provjeri"

CANCELLED = "❌ Otkazano zahtjeva: {count}."

SCREENSHOT_RECEIVED = (
    "📨 Screenshot za <b>{brand}</b> je zaprimljen i poslan na provjeru.\n"
    "Javit ćemo vam se ovdje čim bude provjeren."
)

SCREENSHOT_NEXT = "\n\n⏳ Sljedeći na redu: <b>{brand}</b>. Pošaljite taj screenshot kada budete spremni."

NO_PENDING_FOR_PHOTO = (
    "Trenutno ne očekujem screenshot. Odaberite zemlju i partnera ispod, "
    "a screenshot pošaljite nakon uplate."
)

APPROVED_USER = (
    "✅ <b>Odobreno!</b> Vaša uplata na <b>{brand}</b> je potvrđena.\n\n"
    "Evo vaše osobne poveznice za {vip_name} (vrijedi 24 sata, jednokratna):\n"
    "{invite}\n\n"
    "Dobrodošli u grupu! 🎉"
)

APPROVED_USER_UNTIL = (
    "✅ <b>Odobreno!</b> Vaša uplata na <b>{brand}</b> je potvrđena.\n\n"
    "Evo vaše osobne poveznice za {vip_name} (vrijedi 24 sata, jednokratna):\n"
    "{invite}\n\n"
    "Vaš pristup vrijedi do <b>{until}</b>."
)

APPROVED_NO_LINK = (
    "✅ <b>Odobreno!</b> Vaša uplata na <b>{brand}</b> je potvrđena.\n\n"
    "Došlo je do pogreške pri izradi poveznice — administrator će vam je poslati ručno."
)

REJECTED_USER = (
    "❌ Vaš screenshot za <b>{brand}</b> nije bilo moguće potvrditi.\n\n"
    "Provjerite da screenshot prikazuje uplatu na računu otvorenom putem naše poveznice. "
    "Novi screenshot možete poslati tako da upišete /start.{support}"
)

VIP_EXPIRED = (
    "⌛ Vaš besplatan pristup grupi {vip_name} je istekao.\n\n"
    "Upišite /start za registraciju kod drugog partnera i obnovu pristupa."
)

SUPPORT_SUFFIX = "\n\nPitanja? Pišite na @{username}."

ADMIN_ONLY = "This command is for admins only."

# ---- admin side (EN) ----

ADMIN_REQUEST = (
    "🆕 <b>VIP request #{rid}</b>\n\n"
    "👤 {name} (<code>{user_id}</code>) {username}\n"
    "🌍 Country: {region}\n"
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
