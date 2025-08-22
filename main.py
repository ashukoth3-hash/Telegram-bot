import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("7573978624:AAGFaAbroLTTwwmJEAc-L2Z4-SsdtOJ6y4c") or "7573978624:AAGFaAbroLTTwwmJEAc-L2Z4-SsdtOJ6y4c"
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot live! Try /ping")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    print("🤖 Bot started…")
    app.run_polling()

if __name__ == "__main__":
    main()
