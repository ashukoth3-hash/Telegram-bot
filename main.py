import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Forbidden

# ---- CONFIG ----
BOT_TOKEN = "7573978624:AAGEl85fnNbEpNLgyettFBfzZHYbIXOn6r4"  # <- yaha apna BotFather wala token daala
REQUIRED_CHANNELS = [
    "@free_redeem_codes_fire_crypto",
    "@Free_Fire_Diamond_Hacks_Crypto",
]

# ---- LOGGER ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- START COMMAND ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"👋 Hello {user.first_name}!\n\n"
    text += "👉 Bot use karne ke liye aapko pehle required channels join karne honge:\n\n"
    for ch in REQUIRED_CHANNELS:
        text += f"➡ {ch}\n"
    text += "\nJoin karne ke baad /verify likho."
    await update.message.reply_text(text)

# ---- VERIFY COMMAND ----
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    not_joined = []

    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(ch)
        except Forbidden:
            not_joined.append(ch)

    if not not_joined:
        await update.message.reply_text("✅ Verification successful! Apne sab channels join kar liye 🎉")
    else:
        text = "❌ Aapne abhi tak ye channels join nahi kiye:\n"
        for ch in not_joined:
            text += f"➡ {ch}\n"
        text += "\nJoin karke phir /verify karo."
        await update.message.reply_text(text)

# ---- MAIN ----
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
