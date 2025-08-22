import os, json, asyncio, re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
from telegram.error import Forbidden

# ============ CONFIG ============
BOT_TOKEN = os.getenv("7573978624:AAHhEJ8HZ-Gv_REM4wRRTr3njlf-edgZ44o")  # Render/Replit secrets me set karein

# Join-force channel usernames (WITHOUT @)
REQUIRED_CHANNELS = [
    "free_redeem_codes_fire_crypto",
    "loot4udeal",
]

# Withdrawal proofs / admin review channel (username or numeric id)
PROOF_CHANNEL = "@Withdrawal_Proofsj"  # <-- bot ko is channel me add karna zaroori

# Admin IDs (comma separated if more)
ADMINS = {1898098929}

# Coins
SIGNUP_BONUS = 50
DAILY_BONUS = 10
REFER_COIN = 100

# Withdraw slabs (coins -> label)
WITHDRAW_OPTIONS: List[Tuple[int, str]] = [
    (2000, "2000 Coins = ₹10"),
    (4000, "4000 Coins = ₹20"),
    (6000, "6000 Coins = ₹30"),
]

DB_FILE = "db.json"
DB_LOCK = asyncio.Lock()
db: Dict[str, Any] = {"users": {}}

# ============ DB HELPERS ============
def load_db():
    global db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            db = {"users": {}}
    else:
        db = {"users": {}}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(uid: int) -> Dict[str, Any]:
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "coins": 0,
            "ref_by": None,
            "verified": False,
            "joined_bonus_done": False,
            "last_bonus_date": None,
            "refs": 0,
            "email": None,
        }
    return db["users"][uid]

# ============ UTIL ============
async def is_member(context: ContextTypes.DEFAULT_TYPE, channel: str, user_id: int) -> bool:
    """Check if user is member of a channel."""
    try:
        member = await context.bot.get_chat_member(f"@{channel}", user_id)
        status = member.status
        return status in ("member", "creator", "administrator")
    except Forbidden:
        # Bot not in channel or not allowed to see members
        return False
    except Exception:
        return False

async def is_joined_everywhere(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    results = await asyncio.gather(
        *[is_member(context, ch, user_id) for ch in REQUIRED_CHANNELS]
    )
    return all(results)

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Balance", callback_data="bal"),
            InlineKeyboardButton("👥 Refer", callback_data="ref"),
        ],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")],
        [InlineKeyboardButton("📩 Withdraw", callback_data="wd")],
        [InlineKeyboardButton("🧾 Proof ↗", url="https://t.me/Withdrawal_Proofsj")]
    ])

def join_force_kb() -> InlineKeyboardMarkup:
    btns = [
        [
            InlineKeyboardButton("Join 1 ↗", url=f"https://t.me/{REQUIRED_CHANNELS[0]}"),
            InlineKeyboardButton("Join 2 ↗", url=f"https://t.me/{REQUIRED_CHANNELS[1]}"),
        ],
        [InlineKeyboardButton("✅ Claim 💸", callback_data="claim_join")]
    ]
    return InlineKeyboardMarkup(btns)

WELCOME_TEXT = (
    "🎉 *Swagat hai!*\n"
    "📌 Refer karo, coins banao — aur *redeem codes* withdraw karo!\n\n"
    f"🎁 *Signup Bonus:* {SIGNUP_BONUS} coins\n"
    f"🎁 *Daily Bonus:* {DAILY_BONUS} coins\n"
    f"👥 *Per Refer:* {REFER_COIN} coins"
)

# ============ START / JOIN-FORCE ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    args = context.args or []

    async with DB_LOCK:
        u = get_user(uid)

        # attach referral if present
        if args:
            ref = args[0]
            if ref.isdigit() and int(ref) != uid and u.get("ref_by") is None:
                u["ref_by"] = int(ref)
                save_db()

    # Show join-force if not verified
    async with DB_LOCK:
        verified = get_user(uid).get("verified", False)

    if not verified:
        txt = (
            "😍 *Hey !! User Welcome To Bot*\n\n"
            "🟢 *Must Join All Channels To Use Bot*\n"
            "⬛ *After joining, click Claim*"
        )
        await update.message.reply_text(
            txt, reply_markup=join_force_kb(), parse_mode="Markdown"
        )
        return

    # If already verified, show main menu + welcome
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_menu_kb())

async def claim_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked Claim after joining channels."""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    joined = await is_joined_everywhere(context, uid)

    async with DB_LOCK:
        u = get_user(uid)
        if joined:
            if not u.get("verified", False):
                u["verified"] = True
                # signup bonus once
                if not u.get("joined_bonus_done", False):
                    u["coins"] += SIGNUP_BONUS
                    u["joined_bonus_done"] = True
                # credit referrer
                if u.get("ref_by"):
                    ref_u = get_user(u["ref_by"])
                    ref_u["coins"] += REFER_COIN
                    ref_u["refs"] += 1
            save_db()

    if joined:
        # Show main menu
        await query.edit_message_text(WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_menu_kb())
    else:
        await query.edit_message_text(
            "❌ Abhi sab channels join nahi mile. Pehle dono join karo, phir *Claim* dabao.",
            parse_mode="Markdown",
            reply_markup=join_force_kb(),
        )

# ============ MAIN MENU HANDLERS ============
async def on_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    async with DB_LOCK:
        coins = get_user(uid)["coins"]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"💼 *Your balance:* {coins} coins",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

async def on_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    me = await context.bot.get_me()
    uid = update.effective_user.id
    link = f"https://t.me/{me.username}?start={uid}"
    text = (
        f"🔗 *Referral link:*\n{link}\n\n"
        f"🎯 Har referral par *{REFER_COIN} coins* milenge!"
    )
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())

async def on_daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid = update.effective_user.id
    msg = ""
    async with DB_LOCK:
        u = get_user(uid)
        last = u.get("last_bonus_date")
        today = datetime.utcnow().date().isoformat()
        if last == today:
            msg = "⏳ Aaj ka daily bonus already claim ho chuka hai. Kal fir try karo."
        else:
            u["coins"] += DAILY_BONUS
            u["last_bonus_date"] = today
            save_db()
            msg = f"✅ *Daily bonus added:* +{DAILY_BONUS} coins"
    await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=main_menu_kb())

# ============ WITHDRAW CONVERSATION ============
WD_CHOOSE, WD_EMAIL = range(2)

def withdraw_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(lbl, callback_data=f"wd_{coins}")] for coins, lbl in WITHDRAW_OPTIONS]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

async def on_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    uid = update.effective_user.id
    # check balance first
    async with DB_LOCK:
        coins = get_user(uid)["coins"]
    text = (
        f"💸 *Choose withdrawal option*\n\n"
        f"Your balance: *{coins}* coins\n\n"
        "Select one:"
    )
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=withdraw_keyboard())
    return WD_CHOOSE

async def wd_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await query.edit_message_text(WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_menu_kb())
        return ConversationHandler.END

    if not data.startswith("wd_"):
        return WD_CHOOSE

    coins_needed = int(data.split("_", 1)[1])
    # store in user_data
    context.user_data["wd_coins_needed"] = coins_needed
    # ask email
    await query.edit_message_text(
        "📧 *Enter your Gmail ID* (e.g. `name@gmail.com`):",
        parse_mode="Markdown"
    )
    return WD_EMAIL

EMAIL_RGX = re.compile(r"^[A-Za-z0-9._%+-]+@gmail\.com$")

async def wd_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    email = (update.message.text or "").strip()

    if not EMAIL_RGX.match(email):
        await update.message.reply_text("❌ Please send a valid *Gmail* address (example: `name@gmail.com`).", parse_mode="Markdown")
        return WD_EMAIL

    coins_needed = context.user_data.get("wd_coins_needed")
    if not coins_needed:
        await update.message.reply_text("⚠️ Session expired. Start again: *Withdraw*", parse_mode="Markdown", reply_markup=main_menu_kb())
        return ConversationHandler.END

    # check & deduct
    async with DB_LOCK:
        u = get_user(uid)
        bal = u["coins"]
        if bal < coins_needed:
            await update.message.reply_text(
                f"⚠️ Not enough coins. Required: {coins_needed}, Your balance: {bal}",
                reply_markup=main_menu_kb()
            )
            return ConversationHandler.END

        u["coins"] -= coins_needed
        u["email"] = email
        save_db()

    # find label for chosen coins
    label = next((lbl for c, lbl in WITHDRAW_OPTIONS if c == coins_needed), f"{coins_needed} Coins")

    # push to admin/withdraw channel
    me = await context.bot.get_me()
    text = (
        "📢 *New Withdrawal Request*\n"
        f"🤖 Bot: @{me.username}\n"
        f"👤 User: [{update.effective_user.first_name}](tg://user?id={uid})\n"
        f"🆔 User ID: `{uid}`\n"
        f"💰 Request: *{label}*\n"
        f"📧 Gmail: `{email}`\n"
        "🛠 Admin please process & send code to Gmail."
    )

    try:
        await context.bot.send_message(chat_id=PROOF_CHANNEL, text=text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        # If username failed, try as int if provided
        pass

    await update.message.reply_text(
        "✅ *Request submitted!* Admin will contact you soon.\n"
        "⏳ Processing time: usually within 24h.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    return ConversationHandler.END

async def wd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❎ Withdraw cancelled.", reply_markup=main_menu_kb())
    return ConversationHandler.END

# ============ ADMIN ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMINS:
        return
    async with DB_LOCK:
        total_users = len(db["users"])
    txt = (
        "🛡 *Admin Panel*\n"
        f"👥 Total users: {total_users}\n\n"
        "Commands:\n"
        "`/addcoins <user_id> <amount>`\n"
        "`/setcoins <user_id> <amount>`\n"
        "`/stats`"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    async with DB_LOCK:
        total_users = len(db["users"])
    await update.message.reply_text(f"📊 Users: {total_users}")

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /addcoins <user_id> <amount>")
        return
    target = int(context.args[0]); amt = int(context.args[1])
    async with DB_LOCK:
        u = get_user(target)
        u["coins"] += amt
        save_db()
    await update.message.reply_text(f"✅ Added {amt} coins to {target}")

async def setcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /setcoins <user_id> <amount>")
        return
    target = int(context.args[0]); amt = int(context.args[1])
    async with DB_LOCK:
        u = get_user(target)
        u["coins"] = amt
        save_db()
    await update.message.reply_text(f"✅ Set {target} coins = {amt}")

# ============ ROUTING ============
def make_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set")

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(claim_join, pattern="^claim_join$"))

    # main menu callbacks
    app.add_handler(CallbackQueryHandler(on_balance, pattern="^bal$"))
    app.add_handler(CallbackQueryHandler(on_refer, pattern="^ref$"))
    app.add_handler(CallbackQueryHandler(on_daily_bonus, pattern="^bonus$"))
    app.add_handler(CallbackQueryHandler(on_withdraw, pattern="^wd$"))

    # Withdraw conversation
    wd_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_withdraw, pattern="^wd$")],
        states={
            WD_CHOOSE: [CallbackQueryHandler(wd_choose, pattern="^(wd_\\d+|home)$")],
            WD_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_email)],
        },
        fallbacks=[CommandHandler("cancel", wd_cancel)],
        per_message=False,
    )
    app.add_handler(wd_conv)

    # Admin
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("addcoins", addcoins))
    app.add_handler(CommandHandler("setcoins", setcoins))

    return app

async def on_startup(app: Application):
    load_db()
    print("✅ Bot started...")

def main():
    app = make_app()
    app.post_init = on_startup
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
